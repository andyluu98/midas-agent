import os
import re
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Thêm đường dẫn dự án vào path
sys.path.append(os.getcwd())

from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from tradingagents.dataflows.tradingview_provider import get_tradingview_analysis_report
from tradingagents.dataflows.mt5_provider import (
    get_mt5_data, get_account_summary,
    get_ohlcv_dataframe, get_future_timestamps,
)
from tradingagents.dataflows.kronos_provider import multi_timeframe_forecast
from tradingagents.dataflows.brief_renderer import render_brief
from tradingagents.dataflows.search_provider import print_active_backend
import MetaTrader5 as mt5

# Nạp cấu hình
load_dotenv()


def _confirm_real_account(server: str) -> bool:
    """Cảnh báo + xác nhận khi MT5 server là tài khoản LIVE/Real.
    Trả về True nếu user xác nhận tiếp tục, False nếu huỷ.
    Script này chỉ ĐỌC data nhưng nếu sau này thêm auto-trade sẽ vào lệnh thật.
    """
    if "real" not in server.lower():
        return True  # Demo/Trial — không cần xác nhận
    print()
    print("⚠️ " * 20)
    print(f"⚠️  CẢNH BÁO: TÀI KHOẢN LIVE — Server: {server}")
    print("⚠️  Script hiện CHỈ ĐỌC data, không gửi lệnh.")
    print("⚠️  Nhưng nếu tương lai thêm auto-trade sẽ vào LỆNH THẬT.")
    print("⚠️ " * 20)
    try:
        ans = input("\nTiếp tục với tài khoản REAL? (y/N): ").strip().lower()
    except EOFError:
        ans = ""
    if ans not in ("y", "yes"):
        print("❌ Đã huỷ — chuyển sang demo trước khi chạy.")
        return False
    print("✅ Đã xác nhận. Tiếp tục với tài khoản REAL.\n")
    return True


def _get_m15_forecast(kronos_consensus):
    """Lấy forecast Kronos M15 nếu có và không error."""
    return next(
        (f for f in kronos_consensus.forecasts
         if f.timeframe == "M15" and not f.error),
        None,
    )


def run_ultimate_hunter(ticker="XAUUSD"):
    print("=" * 60)
    print("🚀 ULTIMATE GOLD HUNTER V5 — Scalp M15 (Kronos + TV + DeepSeek) 🚀")
    print("=" * 60)
    print_active_backend()  # In search backend đang dùng

    # 1. LẤY DỮ LIỆU TỪ MT5 (EXNESS) + KIỂM TRA LOẠI TÀI KHOẢN
    print("\n[1/4] Đang kết nối MT5 Exness...")
    mt5_info = get_mt5_data(ticker, mt5.TIMEFRAME_M15, 100)
    acc_info = get_account_summary()

    if "error" in mt5_info:
        print(f"❌ Lỗi MT5: {mt5_info['error']}")
        return

    # Lấy server name từ account_info để cảnh báo Real account
    acc_full = mt5.account_info()
    server = acc_full.server if acc_full else "UNKNOWN"
    if not _confirm_real_account(server):
        return

    real_symbol = mt5_info["symbol"]
    price = mt5_info["current_bid"]
    v_val = mt5_info["last_volume"]
    v_status = mt5_info["volume_status"]
    print(f"✅ Đã kết nối. Giá Exness cho {real_symbol}: {price}")
    print(f"📊 Volume: {v_val} ({v_status}) | 💰 Balance: {acc_info['balance']} {acc_info['currency']}")

    # 2. KRONOS ĐA KHUNG FORECAST (H1 + M15 + M5 — bỏ H4 quá xa cho scalp M15)
    print("\n[2/4] 🔮 Đèn pha Kronos đang dự báo H1/M15/M5...")
    kronos_consensus = multi_timeframe_forecast(
        fetch_ohlcv=get_ohlcv_dataframe,
        fetch_future_ts=get_future_timestamps,
    )
    print(kronos_consensus.summary())

    # GATE: Skip phiên nếu Kronos M15 NEUTRAL (không rõ hướng → không scalp)
    m15_fc = _get_m15_forecast(kronos_consensus)
    if m15_fc is None or m15_fc.direction == "NEUTRAL":
        m15_status = "không có data" if m15_fc is None else f"NEUTRAL (move {m15_fc.move_pct*100:+.2f}%)"
        print()
        print("⏸️  " * 20)
        print(f"⏸️  NO TRADE — Kronos M15 chưa rõ hướng: {m15_status}")
        print("⏸️  Scalper M15 cần khung chính có tín hiệu rõ. Bỏ qua phiên này.")
        print("⏸️  Chờ phiên sau hoặc chuyển sang khung H1/H4 nếu muốn swing.")
        print("⏸️  " * 20)
        return

    # 3. LẤY TÍN HIỆU REAL-TIME TỪ TRADINGVIEW
    print("\n[3/4] 🛡️ Mắt thần TradingView (M5, M15)...")
    tv_m15 = get_tradingview_analysis_report(ticker, "15m")

    # 4. GỌI HỘI ĐỒNG DEEPSEEK — ĐÃ CÓ TÍN HIỆU M15 RÕ
    print("\n[4/4] 🧙 Triệu tập Hội đồng DeepSeek (News, Sentiment, Risk)...")
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "deepseek"
    config["deep_think_llm"] = "deepseek-v4-pro"
    config["quick_think_llm"] = "deepseek-v4-flash"
    config["output_language"] = "Vietnamese"
    config["max_debate_rounds"] = 2
    # Tắt JSON log ~/.tradingagents/logs/.../full_states_log_*.json — đã in
    # CLI và lưu MD ở dưới, không cần dump JSON 36KB nữa.
    config["state_log_enabled"] = False
    config["data_vendors"] = {
        **config.get("data_vendors", {}),
        "news_data": "alpha_vantage",
    }

    ta = TradingAgentsGraph(debug=False, config=config)

    # Ép Council BÁM Kronos M15: SL/TP phải trong [m15.predicted_low, predicted_high]
    # Cap SL tối đa 10 pip ($10 di chuyển) — chống Council vẽ plan kiểu Daily.
    m15_range_low = m15_fc.predicted_low
    m15_range_high = m15_fc.predicted_high
    direction_hint = m15_fc.direction  # BUY hoặc SELL (đã filter NEUTRAL ở trên)

    context_msg = (
        f"BỐI CẢNH SCALP M15 (XAUUSDc):\n"
        f"  Giá Exness: ${price:.2f} | Spread: {mt5_info['spread']:.2f} | "
        f"Volume: {v_status} ({v_val})\n"
        f"  Balance: {acc_info['balance']} {acc_info['currency']}\n\n"
        f"🔮 KRONOS CONSENSUS: {kronos_consensus.direction} "
        f"(Tier {kronos_consensus.confidence_tier})\n"
        f"{kronos_consensus.summary()}\n\n"
        f"🛡️ TRADINGVIEW M15:\n{tv_m15}\n\n"
        f"════ RÀNG BUỘC NGHIÊM (BẮT BUỘC TUÂN) ════\n"
        f"1. ĐÂY LÀ SCALP M15 — KHÔNG dùng level SMA50/Daily/support tuần.\n"
        f"2. Hướng đi Kronos M15 = {direction_hint}. "
        f"Đề xuất MUA/BÁN PHẢI khớp hoặc lý giải vì sao ngược.\n"
        f"3. Entry = ${price:.2f} (giá hiện tại) hoặc gần range Kronos M15.\n"
        f"4. SL PHẢI nằm trong range Kronos M15 [{m15_range_low:.2f}, "
        f"{m15_range_high:.2f}] và KHÔNG xa quá 10 pip = $10 di chuyển.\n"
        f"5. TP PHẢI nằm trong range Kronos M15 (phía đối diện SL).\n"
        f"6. QUY ƯỚC PIP: 1 pip XAUUSD = $1 di chuyển "
        f"(giá $4670 → $4680 = 10 pip).\n"
        f"7. R/R tối thiểu 1:1, mục tiêu 1:1.5-2.\n"
        f"8. Nếu xung đột giữa Kronos M15 và TradingView M15: "
        f"ưu tiên KHÔNG VÀO LỆNH thay vì cưỡng ép.\n"
        f"════════════════════════════════════════════\n\n"
        f"Đưa quyết định MUA/BÁN/ĐỨNG NGOÀI kèm Entry/SL/TP cụ thể (giá Exness)."
    )

    trade_date = datetime.now().strftime("%Y-%m-%d")
    final_state, _ = ta.propagate(ticker, trade_date)

    # In 5 báo cáo phân tích đầy đủ trên CLI (giống session 13/05).
    full_report = _build_full_report(final_state)
    print(full_report)

    # Bản tin cô đọng ~80 dòng — plan + lot deterministic
    brief = render_brief(
        ticker=ticker,
        mt5_info=mt5_info,
        acc_info=acc_info,
        kronos=kronos_consensus,
        tv_m15=tv_m15,
        final_state=final_state,
        llm=ta.quick_thinking_llm,
    )
    print("\n" + brief + "\n")

    # Lưu MD report vào plans/reports/
    md_path = _save_md_report(
        ticker=ticker,
        price=price,
        kronos_summary=kronos_consensus.summary(),
        tv_m15=tv_m15,
        full_report=full_report,
        brief=brief,
    )
    print(f"📁 Báo cáo MD đã lưu: {md_path}")


def _build_full_report(final_state: dict) -> str:
    """Ghép 5 báo cáo phân tích thành một chuỗi để in CLI và lưu MD."""
    sections = [
        ("NEWS REPORT (tin tức vĩ mô + ngành vàng)", final_state.get("news_report", "")),
        ("SENTIMENT REPORT (tâm lý thị trường)", final_state.get("sentiment_report", "")),
        ("FUNDAMENTALS REPORT (yếu tố cơ bản)", final_state.get("fundamentals_report", "")),
        ("INVESTMENT PLAN (Research Manager)", final_state.get("investment_plan", "")),
        ("FINAL TRADE DECISION (Portfolio Manager)", final_state.get("final_trade_decision", "")),
    ]
    parts = []
    for title, body in sections:
        if not body:
            continue
        parts.append(f"\n\n{'─' * 60}\n📰 {title}\n{'─' * 60}\n{body}")
    return "".join(parts)


def _save_md_report(ticker, price, kronos_summary, tv_m15, full_report, brief) -> Path:
    """Lưu báo cáo Markdown vào plans/reports/hunter-{YYMMDD-HHMM}-{ticker}.md."""
    now = datetime.now()
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", ticker.lower()).strip("-")
    fname = f"hunter-{now.strftime('%y%m%d-%H%M')}-{slug}.md"
    out_dir = Path("plans/reports")
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / fname
    md = (
        f"# 🏹 Hunter Report — {ticker} @ ${price:.2f}\n\n"
        f"**Thời điểm:** {now.strftime('%d/%m/%Y %H:%M')} ICT\n\n"
        f"## 🔮 Kronos Consensus\n\n```\n{kronos_summary}\n```\n\n"
        f"## 🛡️ TradingView M15\n\n```\n{tv_m15}\n```\n"
        f"{full_report}\n\n"
        f"---\n\n## 📋 Bản tin tóm tắt\n\n```\n{brief}\n```\n"
    )
    out_path.write_text(md, encoding="utf-8")
    return out_path


if __name__ == "__main__":
    run_ultimate_hunter("XAUUSD")
