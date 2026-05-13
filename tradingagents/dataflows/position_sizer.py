"""Tầng 3 — Thủ kho: tính lot size từ balance + Kronos consensus + SL distance.

Profile B (Balanced) cho user:
- 1% rủi ro/lệnh
- Multiplier theo Kronos consensus (1.2 / 1.0 / 0.5 / 0)
- Cap: max 5 lệnh/ngày, max 5% rủi ro/ngày

Tài khoản Exness Cent: 1 lot Cent ≈ 0.01 standard lot.
"""
from __future__ import annotations

from dataclasses import dataclass

# Profile B (Balanced) — Scalp M15 cho XAUUSD
RISK_PER_TRADE = 0.01          # 1% balance
MAX_TRADES_PER_DAY = 5
MAX_DAILY_RISK = 0.05          # 5%

# Quy ước PIP CÁCH A — 1 pip XAUUSD = $1.00 di chuyển
# (giá $4670 → $4671 = +1 pip, giá $4670 → $4680 = +10 pip)
# Đây là convention nhiều trader VN dùng, đồng nhất với cách user đọc chart.
PIP_SIZE_USD = 1.0             # 1 pip = $1 di chuyển

# Pip value: 1 lot Standard XAUUSD = 100 oz, $1 di chuyển = $100
# Trên Cent account: 1 lot Cent = 1 oz, $1 di chuyển = $1
PIP_VALUE_PER_STANDARD_LOT = 100.0  # $100 / pip / 1 lot standard (vì 1 pip = $1)
CENT_TO_STANDARD = 0.01             # 1 lot Cent = 0.01 standard

# CAP SL cho M15 scalp — không cho SL xa hơn 10 pip ($10 di chuyển)
# Bảo vệ user khỏi plan Daily/Swing lệch khung
MAX_SL_PIPS_M15 = 10
MIN_SL_PIPS = 3                # SL quá gần (<3 pip) thường bị spread/noise quét


@dataclass
class PositionSize:
    direction: str              # BUY/SELL/NO_TRADE
    lot_cent: float             # Lot hiển thị trên MT5 Cent
    lot_standard: float         # Lot quy đổi standard
    risk_usd: float             # Số tiền rủi ro thực (USD)
    sl_pips: float
    tp_pips: float
    reason: str                 # Tại sao chọn lot này

    def summary(self) -> str:
        if self.direction == "NO_TRADE":
            return f"❌ NO TRADE — {self.reason}"
        # Pip Cách A: 1 pip = $1. SL 10 pip = $10 di chuyển.
        return (
            f"💰 {self.direction} | Lot Cent: {self.lot_cent:.2f} "
            f"(={self.lot_standard:.4f} std) | Risk: ${self.risk_usd:.2f} | "
            f"SL: {self.sl_pips:.0f} pip (${self.sl_pips:.0f}) | "
            f"TP: {self.tp_pips:.0f} pip (${self.tp_pips:.0f})\n"
            f"   Lý do: {self.reason}"
        )


def calculate_position(
    balance_usc: float,
    direction: str,
    lot_multiplier: float,
    sl_price: float,
    tp_price: float,
    entry_price: float,
    daily_trades_count: int = 0,
    daily_risk_used: float = 0.0,
) -> PositionSize:
    """Tính lot dựa trên Kronos consensus + risk limits.

    Args:
        balance_usc: Số dư trên Cent account (USC). VD 11000 USC ≈ $110 USD.
        direction: BUY/SELL/NO_TRADE từ Kronos consensus.
        lot_multiplier: 1.2 (A+) / 1.0 (B) / 0.5 (C) / 0 (NO_TRADE).
        sl_price: Giá Stop Loss.
        tp_price: Giá Take Profit.
        entry_price: Giá vào lệnh dự kiến.
        daily_trades_count: Số lệnh đã vào hôm nay (cap MAX_TRADES_PER_DAY).
        daily_risk_used: % balance đã rủi ro hôm nay.

    Returns: PositionSize với reason giải thích.
    """
    # Quy đổi USC → USD thực: 1 USD = 100 USC
    balance_usd = balance_usc / 100.0

    if direction == "NO_TRADE" or lot_multiplier <= 0:
        return PositionSize(
            "NO_TRADE", 0, 0, 0, 0, 0,
            reason="Kronos consensus không đủ tin cậy (≤2/4 khung)"
        )

    if daily_trades_count >= MAX_TRADES_PER_DAY:
        return PositionSize(
            "NO_TRADE", 0, 0, 0, 0, 0,
            reason=f"Đã đạt cap {MAX_TRADES_PER_DAY} lệnh/ngày"
        )

    if daily_risk_used >= MAX_DAILY_RISK:
        return PositionSize(
            "NO_TRADE", 0, 0, 0, 0, 0,
            reason=f"Đã đạt cap {MAX_DAILY_RISK*100:.0f}% rủi ro/ngày"
        )

    # SL/TP pips theo CÁCH A: 1 pip XAUUSD = $1 di chuyển
    sl_pips = abs(entry_price - sl_price) / PIP_SIZE_USD
    tp_pips = abs(tp_price - entry_price) / PIP_SIZE_USD

    if sl_pips < MIN_SL_PIPS:
        return PositionSize(
            "NO_TRADE", 0, 0, 0, 0, 0,
            reason=f"SL quá gần ({sl_pips:.1f} pip < {MIN_SL_PIPS}) — bị spread/noise quét"
        )

    # CAP SL cho M15 scalp — nếu Council/Plan đặt SL xa hơn 10 pip,
    # ép về 10 pip (tránh swing-style SL trên khung M15).
    if sl_pips > MAX_SL_PIPS_M15:
        original_sl_pips = sl_pips
        sl_pips = MAX_SL_PIPS_M15
        # Tính lại sl_price theo direction
        if direction == "BUY":
            sl_price = entry_price - MAX_SL_PIPS_M15 * PIP_SIZE_USD
        else:
            sl_price = entry_price + MAX_SL_PIPS_M15 * PIP_SIZE_USD
        cap_note = f" | SL cap {original_sl_pips:.0f}p → {MAX_SL_PIPS_M15}p (M15 scalp)"
    else:
        cap_note = ""

    # Risk amount USD
    risk_pct = RISK_PER_TRADE * lot_multiplier
    available_risk = MAX_DAILY_RISK - daily_risk_used
    risk_pct = min(risk_pct, available_risk)
    risk_usd = balance_usd * risk_pct

    # Lot standard = risk / (sl_pips × pip_value)
    lot_standard = risk_usd / (sl_pips * PIP_VALUE_PER_STANDARD_LOT)
    lot_standard = round(lot_standard, 4)

    # Quy đổi sang Cent lot — broker MT5 sẽ hiển thị lot này
    lot_cent = lot_standard / CENT_TO_STANDARD
    lot_cent = round(lot_cent, 2)

    if lot_cent < 0.01:
        return PositionSize(
            "NO_TRADE", 0, 0, 0, 0, 0,
            reason=f"Lot tính ra quá nhỏ ({lot_cent} Cent < 0.01 min) — balance không đủ"
        )

    return PositionSize(
        direction=direction,
        lot_cent=lot_cent,
        lot_standard=lot_standard,
        risk_usd=risk_usd,
        sl_pips=sl_pips,
        tp_pips=tp_pips,
        reason=f"Multiplier={lot_multiplier}x, risk={risk_pct*100:.2f}%, RR={tp_pips/sl_pips:.2f}{cap_note}",
    )
