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
from tradingagents.dataflows.position_sizer import calculate_position
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

    ta = TradingAgentsGraph(debug=False, config=config)

    # Gợi ý SL/TP từ Kronos M15 forecast (range)
    m15_fc = next((f for f in kronos_consensus.forecasts if f.timeframe == "M15" and not f.error), None)
    sl_hint, tp_hint = "(không có)", "(không có)"
    if m15_fc:
        if kronos_consensus.direction == "BUY":
            sl_hint = f"{m15_fc.predicted_low:.2f}"
            tp_hint = f"{m15_fc.predicted_high:.2f}"
        elif kronos_consensus.direction == "SELL":
            sl_hint = f"{m15_fc.predicted_high:.2f}"
            tp_hint = f"{m15_fc.predicted_low:.2f}"

    context_msg = f"""
--- BÁO CÁO TỪ CHIẾN TRƯỜNG ---
GIÁ EXNESS: {price} | VOLUME: {v_status} ({v_val})
SỐ DƯ HANG: {acc_info['balance']} {acc_info['currency']}

🔮 KRONOS DỰ BÁO ĐA KHUNG (đèn pha tương lai):
{kronos_consensus.summary()}

   SL gợi ý từ M15 forecast range: {sl_hint}
   TP gợi ý từ M15 forecast range: {tp_hint}
   Lot multiplier theo consensus: {kronos_consensus.lot_multiplier}x

🛡️ TÍN HIỆU MẮT THẦN (TRADINGVIEW M15):
{tv_m15}

NHIỆM VỤ CỦA HỘI ĐỒNG:
1. THẦN TÀI (News): Soi tin Fed, chính trị 1h qua, có sự kiện CPI/NFP/FOMC sắp ra không.
2. GƯƠNG THẦN (Sentiment): Soi tâm lý đám đông Reddit/Twitter.
3. NHẬT KÝ (Memory): Nhắc lại các lỗi lầm cũ khi trade vàng.
4. THỦ KHO (Risk): Lot Cent đã tính tự động ở Tier 3 — chỉ confirm nếu phù hợp với risk profile.

YÊU CẦU QUYẾT ĐỊNH CUỐI CÙNG: MUA/BÁN/ĐỨNG NGOÀI?
- Nếu MUA/BÁN: kèm Entry, SL, TP chuẩn giá Exness, đối chiếu với Kronos forecast.
- Nếu ĐỨNG NGOÀI: nêu lý do (Kronos conflict / tin xấu / tâm lý ngược).
"""
    
    trade_date = datetime.now().strftime("%Y-%m-%d")
    
    print("\n" + "💎"*20)
    print("BẢN TIN CHIẾN THUẬT CUỐI CÙNG")
    print("💎"*20)
    print(f"\n{context_msg}")
    print("-" * 30)
    
    _, decision = ta.propagate(ticker, trade_date)
    print(decision)

    # TẦNG 3: THỦ KHO TÍNH LOT
    print("\n" + "💰" * 20)
    print("TẦNG 3 — THỦ KHO TÍNH LOT")
    print("💰" * 20)
    if m15_fc and kronos_consensus.direction in ("BUY", "SELL"):
        if kronos_consensus.direction == "BUY":
            sl_p, tp_p = m15_fc.predicted_low, m15_fc.predicted_high
        else:
            sl_p, tp_p = m15_fc.predicted_high, m15_fc.predicted_low
        pos = calculate_position(
            balance_usc=float(acc_info["balance"]),
            direction=kronos_consensus.direction,
            lot_multiplier=kronos_consensus.lot_multiplier,
            sl_price=sl_p,
            tp_price=tp_p,
            entry_price=price,
        )
        print(pos.summary())
    else:
        print("❌ NO TRADE — Kronos không cho tín hiệu rõ ràng, Thủ kho không vào lệnh.")

    print("\n" + "="*60)

if __name__ == "__main__":
    run_ultimate_hunter("XAUUSD")
