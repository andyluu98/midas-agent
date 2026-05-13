"""Render a concise Vietnamese gold-hunter brief from raw council state.

The Trading Agents council produces five long reports (market, news,
sentiment, fundamentals, investment plan) totalling ~30 KB. For users
running the hunter inside Claude Code or any chat surface, that volume
is unreadable.

This module condenses council output into an ~80-line brief covering:
price snapshot, Kronos multi-TF table, TradingView signal, news bullets
grouped by direction, council debate (phe MUA vs phe BÁN), and a
concrete trade plan with entry/SL/TP/lot/RR. Deterministic blocks are
formatted in Python; the narrative blocks (news/debate/plan) come from
a single LLM call so the trader-facing tone reads like a market briefing
rather than a dump of section headers. The full reports remain saved to
``~/.tradingagents/logs/<TICKER>/...json`` for deep reviews.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

from tradingagents.dataflows.position_sizer import calculate_position

logger = logging.getLogger(__name__)


_BRIEF_PROMPT = """Bạn là chuyên gia tóm tắt bản tin giao dịch vàng XAUUSD bằng tiếng Việt.
Đầu vào là các báo cáo dài của hội đồng phân tích. Hãy nén thành bản tin
ngắn gọn theo ĐÚNG cấu trúc bên dưới.

QUY TẮC NGHIÊM:
- Tuyệt đối KHÔNG dùng "bull/bear" — dùng "phe MUA / phe BÁN".
- Tin tức: 4-5 sự kiện đẩy giá lên + 3-4 sự kiện kéo giá xuống. Mỗi dòng
  một sự kiện kèm 1 câu giải thích NGẮN vì sao ảnh hưởng vàng. Văn phong
  tự nhiên cho trader đọc, không phải báo cáo kỹ thuật khô cứng.
- Phe MUA / phe BÁN: 3-4 ý mỗi phe, ngắn, không thuật ngữ rườm rà.
- Plan giao dịch: trích chính xác các con số Entry/SL/TP từ Portfolio
  Manager. 1 pip XAUUSD = 0.01 (giá 4490 → 4350 cách 14000 pip).
  Tính R/R = |TP - Entry| / |Entry - SL|.
- Nếu Kronos NO_TRADE: HÀNH ĐỘNG NGAY = "❌ KHÔNG MỞ LỆNH MỚI" và liệt
  kê 2-3 kịch bản chờ đợi (giá nào thì vào mua/bán).
- Không tự bịa số: chỉ dùng giá xuất hiện trong Portfolio Manager report.

DỮ LIỆU NGỮ CẢNH:
Giá hiện tại: ${PRICE}
Kronos verdict: {KRONOS_DIRECTION} (consensus {KRONOS_AGREE}/{KRONOS_TOTAL})
Balance: {BALANCE} {CURRENCY}

NEWS REPORT (đầy đủ):
{NEWS}

SENTIMENT REPORT:
{SENTIMENT}

INVESTMENT PLAN (Research Manager):
{PLAN}

FINAL TRADE DECISION (Portfolio Manager — nguồn số liệu plan):
{PM}

ĐẦU RA: Chỉ phần text bên dưới, KHÔNG code fence, GIỮ NGUYÊN emoji và
indent (3 space cho nhóm, 5 space cho bullet):

📰 TÌNH HÌNH TIN TỨC
   📈 Đẩy giá VÀNG lên:
     • <sự kiện> — <ảnh hưởng>
     • <sự kiện> — <ảnh hưởng>
   📉 Kéo giá VÀNG xuống:
     • <sự kiện> — <ảnh hưởng>

⚖️ HỘI ĐỒNG TRANH LUẬN
   📈 Phe MUA cho rằng:
     • <ý>
   📉 Phe BÁN cho rằng:
     • <ý>
   → Kết luận: <1 dòng>

🎯 PLAN GIAO DỊCH (giá Exness, lot Cent)
   HÀNH ĐỘNG NGAY: <action ngắn>

   KỊCH BẢN A — <tên>:
   🟢 Entry $X.XX | SL $Y.YY (-Zpip) | TP $W.WW (+Vpip) | R/R 1:N.NN

   KỊCH BẢN B — <tên>:
   🟢 Entry ... | SL ... | TP ... | R/R ...

   ⚠️ <điều cần tránh>
"""


def _render_kronos_table(kronos) -> str:
    lines = [
        f"🔮 KRONOS 4 KHUNG → {kronos.direction} "
        f"({kronos.aligned_count}/{kronos.total_count} đồng thuận, "
        f"Tier {kronos.confidence_tier})"
    ]
    for fc in kronos.forecasts:
        if fc.error:
            lines.append(f"   {fc.timeframe:<3} ERROR — {fc.error}")
            continue
        lines.append(
            f"   {fc.timeframe:<3} {fc.direction:<7} "
            f"{fc.move_pct * 100:+.2f}% → {fc.predicted_mean:.2f}  "
            f"[{fc.predicted_low:.2f} - {fc.predicted_high:.2f}]"
        )
    return "\n".join(lines)


def _render_tv_summary(tv_report: str) -> str:
    """Pull RECOMMENDATION + counts + key indicators from the TV markdown."""
    # Match RECOMMENDATION (BUY/SELL/NEUTRAL/STRONG_*) near TỔNG/TONG KET.
    rec = re.search(r"T[ỔO]NG\s*K[ẾE]T.*?\*\*([A-Z_]+)\*\*", tv_report)
    # BÁN / BAN both accepted — same for TRUNG LẬP / TRUNG LAP — so the
    # parser stays correct when the TradingView provider strips diacritics
    # (e.g. on Windows consoles where the locale forces ASCII).
    buy = re.search(r"MUA:\s*(\d+)", tv_report)
    sell = re.search(r"B[ÁA]N:\s*(\d+)", tv_report)
    neutral = re.search(r"TRUNG\s+L[ẬA]P:\s*(\d+)", tv_report)
    rsi = re.search(r"RSI[^:]*:\s*([\d.]+|N/A)", tv_report)
    macd = re.search(r"MACD Level:\s*([+\-\d.]+|N/A)", tv_report)
    adx = re.search(r"ADX[^:]*:\s*([\d.]+|N/A)", tv_report)
    vwap = re.search(r"VWAP[^:]*:\s*([\d.]+|N/A)", tv_report)
    bb_u = re.search(r"Bollinger Upper:\s*([\d.]+|N/A)", tv_report)
    bb_l = re.search(r"Bollinger Lower:\s*([\d.]+|N/A)", tv_report)

    head = (
        f"🛡️ TRADINGVIEW M15 → {rec.group(1) if rec else 'N/A'} "
        f"({buy.group(1) if buy else '?'} mua / "
        f"{sell.group(1) if sell else '?'} bán / "
        f"{neutral.group(1) if neutral else '?'} trung lập)"
    )
    inds = (
        f"   RSI {rsi.group(1) if rsi else 'N/A'}  "
        f"MACD {macd.group(1) if macd else 'N/A'}  "
        f"ADX {adx.group(1) if adx else 'N/A'}  "
        f"VWAP {vwap.group(1) if vwap else 'N/A'}"
    )
    parts = [head, inds]
    if bb_l and bb_u:
        parts.append(f"   Bollinger Band: [{bb_l.group(1)} - {bb_u.group(1)}]")
    return "\n".join(parts)


def _render_lot(kronos, balance, entry_price) -> str:
    m15 = next(
        (f for f in kronos.forecasts if f.timeframe == "M15" and not f.error),
        None,
    )
    if kronos.direction == "NO_TRADE" or not m15:
        return (
            "💰 THỦ KHO TÍNH LOT\n"
            "   ❌ NO TRADE — Kronos không cho tín hiệu rõ, không vào lệnh."
        )
    if kronos.direction == "BUY":
        sl_p, tp_p = m15.predicted_low, m15.predicted_high
    else:
        sl_p, tp_p = m15.predicted_high, m15.predicted_low
    pos = calculate_position(
        balance_usc=float(balance),
        direction=kronos.direction,
        lot_multiplier=kronos.lot_multiplier,
        sl_price=sl_p,
        tp_price=tp_p,
        entry_price=entry_price,
    )
    # Indent the position summary so it fits the brief style.
    indented = "\n".join(f"   {line}" for line in pos.summary().splitlines())
    return f"💰 THỦ KHO TÍNH LOT\n{indented}"


def _build_narrative(state, kronos, price, balance, currency, llm) -> str | None:
    if llm is None:
        return None
    prompt = _BRIEF_PROMPT.format(
        PRICE=f"{price:.2f}",
        KRONOS_DIRECTION=kronos.direction,
        KRONOS_AGREE=kronos.aligned_count,
        KRONOS_TOTAL=kronos.total_count,
        BALANCE=balance,
        CURRENCY=currency,
        NEWS=state.get("news_report", "(không có)"),
        SENTIMENT=state.get("sentiment_report", "(không có)"),
        PLAN=state.get("investment_plan", "(không có)"),
        PM=state.get("final_trade_decision", "(không có)"),
    )
    try:
        resp = llm.invoke([{"role": "user", "content": prompt}])
        return resp.content if hasattr(resp, "content") else str(resp)
    except Exception as exc:
        logger.warning("brief_renderer: LLM summarizer failed (%s)", exc)
        return None


def render_brief(
    *,
    ticker: str,
    mt5_info: dict,
    acc_info: dict,
    kronos,
    tv_m15: str,
    final_state: dict,
    llm,
) -> str:
    """Return the user-facing ~80-line concise brief."""
    now = datetime.now().strftime("%d/%m/%Y %H:%M ICT")
    price = mt5_info["current_bid"]
    balance = acc_info["balance"]
    max_risk = balance * 0.01

    header = (
        f"🏹 BẢN TIN SĂN VÀNG — {mt5_info['symbol']} {now}\n"
        f"{'═' * 60}\n"
        f"💰 Giá: ${price:.2f}  |  Spread: {mt5_info['spread']:.2f}  |  "
        f"Volume: {mt5_info['volume_status']} ({mt5_info['last_volume']})\n"
        f"🏦 Balance: {balance:.0f} {acc_info['currency']}  |  "
        f"Max risk/lệnh: ~${max_risk / 100:.2f} (1% — TK Cent)"
    )

    narrative = _build_narrative(
        final_state, kronos, price, balance, acc_info["currency"], llm
    )
    if narrative is None:
        # LLM failed — fall back to a trimmed PM decision so the brief still
        # contains actionable plan text instead of going silent.
        pm = final_state.get("final_trade_decision", "(không có)")
        narrative = (
            "📰 TÌNH HÌNH TIN TỨC + ⚖️ TRANH LUẬN: (LLM lỗi — xem file log)\n\n"
            "🎯 PLAN GIAO DỊCH (raw từ Portfolio Manager):\n"
            f"{pm[:1800]}{'...' if len(pm) > 1800 else ''}"
        )

    log_path = (
        Path.home() / ".tradingagents/logs" / ticker /
        "TradingAgentsStrategy_logs" /
        f"full_states_log_{datetime.now().strftime('%Y-%m-%d')}.json"
    )
    footer = (
        f"\n{'═' * 60}\n"
        f"📁 Báo cáo chi tiết (5 reports đầy đủ):\n"
        f"   {log_path}"
    )

    return "\n\n".join([
        header,
        _render_kronos_table(kronos),
        _render_tv_summary(tv_m15),
        narrative,
        _render_lot(kronos, balance, price),
    ]) + footer
