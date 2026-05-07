"""Tầng 3 — Thủ kho: tính lot size từ balance + Kronos consensus + SL distance.

Profile B (Balanced) cho user:
- 1% rủi ro/lệnh
- Multiplier theo Kronos consensus (1.2 / 1.0 / 0.5 / 0)
- Cap: max 5 lệnh/ngày, max 5% rủi ro/ngày

Tài khoản Exness Cent: 1 lot Cent ≈ 0.01 standard lot.
"""
from __future__ import annotations

from dataclasses import dataclass

# Profile B (Balanced)
RISK_PER_TRADE = 0.01          # 1% balance
MAX_TRADES_PER_DAY = 5
MAX_DAILY_RISK = 0.05          # 5%

# Pip value cho XAUUSD trên 1 standard lot — $1 di chuyển = $100 (vì 1 lot = 100 oz)
# Trên Cent account: 1 Cent lot = 1 oz, $1 di chuyển = $1 → pip value $0.01/pip standard, $0.0001/pip Cent
# Quy ước pip XAUUSD: 1 pip = 0.01 (giá $3500.05 → 3500.06 = +1 pip)
PIP_VALUE_PER_STANDARD_LOT = 1.0       # $1 / pip / 1 standard lot XAUUSD
CENT_TO_STANDARD = 0.01                # 1 lot Cent = 0.01 standard


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
        return (
            f"💰 {self.direction} | Lot Cent: {self.lot_cent:.2f} "
            f"(={self.lot_standard:.4f} std) | Risk: ${self.risk_usd:.2f} | "
            f"SL: {self.sl_pips:.0f}p | TP: {self.tp_pips:.0f}p\n"
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

    # SL/TP pips (1 pip XAUUSD = 0.01)
    sl_pips = abs(entry_price - sl_price) / 0.01
    tp_pips = abs(tp_price - entry_price) / 0.01

    if sl_pips < 5:
        return PositionSize(
            "NO_TRADE", 0, 0, 0, 0, 0,
            reason=f"SL quá gần ({sl_pips:.1f} pips < 5) — risk-reward kém"
        )

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
        reason=f"Multiplier={lot_multiplier}x, risk={risk_pct*100:.2f}%, RR={tp_pips/sl_pips:.2f}",
    )
