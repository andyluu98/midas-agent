import os
import sys
from datetime import datetime
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
import MetaTrader5 as mt5

# Nạp cấu hình
load_dotenv()

def run_ultimate_hunter(ticker="XAUUSD"):
    print("="*60)
    print("🚀 ULTIMATE GOLD HUNTER V4 — 3 TẦNG AI (Kronos + Watcher + DeepSeek) 🚀")
    print("="*60)

    # 1. LẤY DỮ LIỆU TỪ MT5 (EXNESS)
    print("\n[1/4] Đang kết nối MT5 Exness...")
    mt5_info = get_mt5_data(ticker, mt5.TIMEFRAME_M15, 100)
    acc_info = get_account_summary()

    if "error" in mt5_info:
        print(f"❌ Lỗi MT5: {mt5_info['error']}")
        return

    real_symbol = mt5_info['symbol']
    price = mt5_info['current_bid']
    v_val = mt5_info['last_volume']
    v_status = mt5_info['volume_status']
    print(f"✅ Đã kết nối. Giá Exness cho {real_symbol}: {price}")
    print(f"📊 Volume: {v_val} ({v_status}) | 💰 Balance: {acc_info['balance']} {acc_info['currency']}")

    # 2. KRONOS ĐA KHUNG FORECAST
    print("\n[2/4] 🔮 Đèn pha Kronos đang dự báo H4/H1/M15/M5...")
    kronos_consensus = multi_timeframe_forecast(
        fetch_ohlcv=get_ohlcv_dataframe,
        fetch_future_ts=get_future_timestamps,
    )
    print(kronos_consensus.summary())

    # 3. LẤY TÍN HIỆU REAL-TIME TỪ TRADINGVIEW
    print("\n[3/4] 🛡️ Mắt thần TradingView (M5, M15)...")
    tv_m5 = get_tradingview_analysis_report(ticker, "5m")
    tv_m15 = get_tradingview_analysis_report(ticker, "15m")

    # 4. GỌI GIÀ LÀNG DEEPSEEK VÀ CÁC THẦN BINH
    print("\n[4/4] 🧙 Triệu tập Hội đồng DeepSeek (News, Sentiment, Risk)...")
    config = DEFAULT_CONFIG.copy()
    config["llm_provider"] = "deepseek"
    config["deep_think_llm"] = "deepseek-v4-pro"
    config["quick_think_llm"] = "deepseek-v4-flash"
    config["output_language"] = "Vietnamese"
    config["max_debate_rounds"] = 2
    # Alpha Vantage có news endpoint cho commodity; yfinance không có news cho
    # XAUUSD spot, dẫn đến News Analyst phải scrape rất chật vật.
    config["data_vendors"] = {
        **config.get("data_vendors", {}),
        "news_data": "alpha_vantage",
    }

    ta = TradingAgentsGraph(debug=False, config=config)

    # Hội đồng nhận context cô đọng: giá, Kronos snapshot, TradingView M15.
    # Plan/SL/TP chi tiết do Portfolio Manager trong council tự sinh ra,
    # rồi brief_renderer trích lại thành plan ngắn cho user.
    context_msg = (
        f"GIÁ EXNESS: {price} | VOLUME: {v_status} ({v_val}) | "
        f"BALANCE: {acc_info['balance']} {acc_info['currency']}\n\n"
        f"🔮 KRONOS:\n{kronos_consensus.summary()}\n\n"
        f"🛡️ TRADINGVIEW M15:\n{tv_m15}\n\n"
        f"Hãy đưa quyết định MUA/BÁN/ĐỨNG NGOÀI kèm Entry/SL/TP cụ thể "
        f"(giá Exness), đối chiếu với Kronos forecast và bối cảnh tin tức."
    )

    trade_date = datetime.now().strftime("%Y-%m-%d")
    final_state, _ = ta.propagate(ticker, trade_date)

    # Bản tin cô đọng ~80 dòng cho user đọc trên Claude Code / terminal.
    # 5 báo cáo dài đầy đủ vẫn được TradingAgentsGraph tự lưu vào
    # ~/.tradingagents/logs/<TICKER>/...json cho ai cần đào sâu.
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

if __name__ == "__main__":
    run_ultimate_hunter("XAUUSD")
