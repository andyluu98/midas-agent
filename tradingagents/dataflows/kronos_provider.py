"""Kronos foundation model wrapper — multi-timeframe forecast cho XAUUSD.

Thiết kế:
- Singleton lazy-load model (chỉ load 1 lần khi gọi đầu tiên).
- Multi-timeframe parallel forecast (ThreadPoolExecutor).
- Consensus aggregator: 4/4 = A+, 3/4 = B, ≤2 = NO TRADE.

Dùng vendored Kronos source code trong `kronos_vendor/`.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import Optional

import pandas as pd

# Cấu hình mặc định cho scalp M15 — bỏ H4 (quá xa, 24h tới không liên quan
# scalper M15 chỉ giữ lệnh 1-4 giờ). Giữ H1 làm nền, M15 chính, M5 xác nhận.
# Threshold M15 nâng lên 0.3% (từ 0.1%) để giảm noise — XAUUSD ~$4700,
# 0.3% = $14 ≈ 1 nến M15 trung bình, đủ rõ hướng đi.
DEFAULT_TF_CONFIG = {
    # tf_label: (lookback bars, pred_len bars, direction threshold %)
    "H1":  (400, 12, 0.004),  # 12h tới, threshold ±0.4% — nền context
    "M15": (400, 16, 0.003),  # 4h tới, threshold ±0.3% — KHUNG CHÍNH (scalp)
    "M5":  (400, 12, 0.0015), # 1h tới, threshold ±0.15% — xác nhận entry
}

MODEL_NAME = "NeoQuasar/Kronos-small"
TOKENIZER_NAME = "NeoQuasar/Kronos-Tokenizer-base"


@dataclass
class TimeframeForecast:
    timeframe: str
    direction: str               # "BUY" / "SELL" / "NEUTRAL"
    current_close: float
    predicted_mean: float
    predicted_high: float
    predicted_low: float
    move_pct: float              # (predicted_mean - current) / current
    forecast_df: Optional[pd.DataFrame] = None
    error: Optional[str] = None


@dataclass
class ConsensusResult:
    direction: str               # "BUY" / "SELL" / "NO_TRADE"
    aligned_count: int           # số khung cùng chiều với direction
    total_count: int
    confidence_tier: str         # "A+", "B", "NO_TRADE"
    lot_multiplier: float        # 1.2 / 1.0 / 0.5 / 0.0
    forecasts: list[TimeframeForecast] = field(default_factory=list)

    def summary(self) -> str:
        lines = [f"KRONOS CONSENSUS: {self.direction} ({self.aligned_count}/{self.total_count}) — Tier {self.confidence_tier}"]
        for f in self.forecasts:
            if f.error:
                lines.append(f"  [{f.timeframe}] LỖI: {f.error}")
            else:
                lines.append(
                    f"  [{f.timeframe}] {f.direction} | now={f.current_close:.2f} "
                    f"→ pred={f.predicted_mean:.2f} ({f.move_pct*100:+.2f}%) "
                    f"range=[{f.predicted_low:.2f}, {f.predicted_high:.2f}]"
                )
        return "\n".join(lines)


class KronosProvider:
    """Singleton wrapper. Gọi `KronosProvider.get()` để lấy instance."""

    _instance: Optional["KronosProvider"] = None
    _lock = threading.Lock()

    def __init__(self):
        self._predictor = None
        self._load_lock = threading.Lock()
        # KronosPredictor có internal state, không safe cho parallel thread → serialize predict()
        self._predict_lock = threading.Lock()

    @classmethod
    def get(cls) -> "KronosProvider":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def _ensure_loaded(self):
        if self._predictor is not None:
            return
        with self._load_lock:
            if self._predictor is not None:
                return
            print(f"[Kronos] Loading {MODEL_NAME} (lần đầu sẽ tải ~100MB)...")
            from .kronos_vendor import Kronos, KronosTokenizer, KronosPredictor
            tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_NAME)
            model = Kronos.from_pretrained(MODEL_NAME)
            self._predictor = KronosPredictor(model, tokenizer, max_context=512)
            print("[Kronos] Model loaded.")

    def forecast_one(
        self,
        df: pd.DataFrame,
        timeframe: str,
        lookback: int,
        pred_len: int,
        threshold: float,
        future_timestamps: pd.Series,
    ) -> TimeframeForecast:
        """Dự báo cho 1 khung. df cần có open/high/low/close/volume + 1 cột timestamp."""
        try:
            self._ensure_loaded()

            # Lấy lookback gần nhất
            df_in = df.tail(lookback).reset_index(drop=True)
            x_df = df_in[["open", "high", "low", "close", "volume"]].copy()
            x_ts = pd.to_datetime(df_in["time"]) if "time" in df_in.columns else pd.to_datetime(df_in.index)

            current_close = float(df_in["close"].iloc[-1])

            # Serialize inference vì predictor không thread-safe
            with self._predict_lock:
                pred_df = self._predictor.predict(
                    df=x_df,
                    x_timestamp=x_ts,
                    y_timestamp=future_timestamps,
                    pred_len=pred_len,
                    T=0.8,
                    top_p=0.9,
                    sample_count=1,
                    verbose=False,
                )

            pred_mean = float(pred_df["close"].mean())
            pred_high = float(pred_df["high"].max())
            pred_low = float(pred_df["low"].min())
            move_pct = (pred_mean - current_close) / current_close

            if move_pct >= threshold:
                direction = "BUY"
            elif move_pct <= -threshold:
                direction = "SELL"
            else:
                direction = "NEUTRAL"

            return TimeframeForecast(
                timeframe=timeframe,
                direction=direction,
                current_close=current_close,
                predicted_mean=pred_mean,
                predicted_high=pred_high,
                predicted_low=pred_low,
                move_pct=move_pct,
                forecast_df=pred_df,
            )
        except Exception as e:
            return TimeframeForecast(
                timeframe=timeframe,
                direction="NEUTRAL",
                current_close=0.0,
                predicted_mean=0.0,
                predicted_high=0.0,
                predicted_low=0.0,
                move_pct=0.0,
                error=str(e),
            )


def _consensus(forecasts: list[TimeframeForecast]) -> ConsensusResult:
    """Đếm số khung cùng chiều và quyết định tier."""
    valid = [f for f in forecasts if f.error is None and f.direction != "NEUTRAL"]
    total = len(forecasts)

    buy_count = sum(1 for f in valid if f.direction == "BUY")
    sell_count = sum(1 for f in valid if f.direction == "SELL")

    if buy_count > sell_count:
        direction = "BUY"
        aligned = buy_count
    elif sell_count > buy_count:
        direction = "SELL"
        aligned = sell_count
    else:
        direction = "NO_TRADE"
        aligned = max(buy_count, sell_count)

    if aligned == total and total >= 3:
        tier, mult = "A+", 1.2
    elif aligned >= total - 1 and total >= 3:
        tier, mult = "B", 1.0
    elif aligned >= total // 2 + 1:
        tier, mult = "C", 0.5
    else:
        direction, tier, mult = "NO_TRADE", "NO_TRADE", 0.0

    return ConsensusResult(
        direction=direction,
        aligned_count=aligned,
        total_count=total,
        confidence_tier=tier,
        lot_multiplier=mult,
        forecasts=forecasts,
    )


def multi_timeframe_forecast(
    fetch_ohlcv: callable,
    fetch_future_ts: callable,
    timeframes: list[str] = None,
    config: dict = None,
) -> ConsensusResult:
    """Chạy forecast 4 khung song song.

    Args:
        fetch_ohlcv(tf_label, lookback) -> DataFrame OHLCV với cột 'time'
        fetch_future_ts(tf_label, pred_len) -> pd.Series các timestamp tương lai
        timeframes: list ["H4", "H1", "M15", "M5"]. Mặc định lấy theo DEFAULT_TF_CONFIG.
        config: dict override DEFAULT_TF_CONFIG.

    Returns: ConsensusResult.
    """
    cfg = {**DEFAULT_TF_CONFIG, **(config or {})}
    tfs = timeframes or list(cfg.keys())
    provider = KronosProvider.get()
    provider._ensure_loaded()  # Load trước khi parallel — tránh race tải model

    def task(tf):
        lookback, pred_len, threshold = cfg[tf]
        try:
            df = fetch_ohlcv(tf, lookback)
            if df is None or df.empty:
                return TimeframeForecast(tf, "NEUTRAL", 0, 0, 0, 0, 0, error="No OHLCV data")
            future_ts = fetch_future_ts(tf, pred_len)
            return provider.forecast_one(df, tf, lookback, pred_len, threshold, future_ts)
        except Exception as e:
            return TimeframeForecast(tf, "NEUTRAL", 0, 0, 0, 0, 0, error=str(e))

    results = []
    with ThreadPoolExecutor(max_workers=len(tfs)) as ex:
        futures = {ex.submit(task, tf): tf for tf in tfs}
        for fut in as_completed(futures):
            results.append(fut.result())

    # Sắp xếp theo thứ tự gốc để dễ đọc
    order = {tf: i for i, tf in enumerate(tfs)}
    results.sort(key=lambda f: order.get(f.timeframe, 99))

    return _consensus(results)
