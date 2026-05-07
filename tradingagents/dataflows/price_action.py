"""Price action patterns + Bollinger squeeze detection từ OHLC dataframe MT5.

Tất cả hàm nhận DataFrame có cột: open, high, low, close, tick_volume.
Pattern detection theo định nghĩa kinh điển — không có ML, dễ debug.
"""
from __future__ import annotations

import pandas as pd


def _body(row) -> float:
    return abs(row["close"] - row["open"])


def _upper_wick(row) -> float:
    return row["high"] - max(row["close"], row["open"])


def _lower_wick(row) -> float:
    return min(row["close"], row["open"]) - row["low"]


def is_bullish_engulfing(df: pd.DataFrame) -> bool:
    """Cây xanh hiện tại phủ trùm cây đỏ trước đó."""
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    return (
        prev["close"] < prev["open"]                       # cây trước đỏ
        and curr["close"] > curr["open"]                   # cây hiện tại xanh
        and curr["close"] >= prev["open"]                  # phủ thân
        and curr["open"] <= prev["close"]
    )


def is_bearish_engulfing(df: pd.DataFrame) -> bool:
    if len(df) < 2:
        return False
    prev, curr = df.iloc[-2], df.iloc[-1]
    return (
        prev["close"] > prev["open"]
        and curr["close"] < curr["open"]
        and curr["open"] >= prev["close"]
        and curr["close"] <= prev["open"]
    )


def is_pinbar_bullish(row, wick_ratio: float = 2.0) -> bool:
    """Pinbar đáy: râu dưới >= 2x thân, râu trên ngắn → reject xuống."""
    body = _body(row)
    if body == 0:
        return False
    return (
        _lower_wick(row) >= wick_ratio * body
        and _upper_wick(row) <= body
    )


def is_pinbar_bearish(row, wick_ratio: float = 2.0) -> bool:
    body = _body(row)
    if body == 0:
        return False
    return (
        _upper_wick(row) >= wick_ratio * body
        and _lower_wick(row) <= body
    )


def detect_candlestick_pattern(df: pd.DataFrame) -> tuple[str | None, str]:
    """Trả về (pattern_name, direction) — direction là 'BUY' / 'SELL' / None."""
    if len(df) < 2:
        return None, ""
    last = df.iloc[-1]
    if is_bullish_engulfing(df):
        return "Bullish Engulfing", "BUY"
    if is_bearish_engulfing(df):
        return "Bearish Engulfing", "SELL"
    if is_pinbar_bullish(last):
        return "Pinbar đáy (rejection)", "BUY"
    if is_pinbar_bearish(last):
        return "Pinbar đỉnh (rejection)", "SELL"
    return None, ""


def bollinger_squeeze_score(
    df: pd.DataFrame,
    period: int = 20,
    std: float = 2.0,
    quantile: float = 0.2,
) -> tuple[bool, float]:
    """Phát hiện BB siết chặt — bandwidth dưới percentile thấp lịch sử.

    Trả về (is_squeezing, current_bandwidth).
    """
    if len(df) < period + 5:
        return False, 0.0
    sma = df["close"].rolling(period).mean()
    std_dev = df["close"].rolling(period).std()
    upper = sma + std * std_dev
    lower = sma - std * std_dev
    bandwidth = (upper - lower) / sma
    threshold = bandwidth.dropna().quantile(quantile)
    current = bandwidth.iloc[-1]
    return bool(current <= threshold), float(current)
