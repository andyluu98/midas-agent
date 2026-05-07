from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv
import os

# Nạp API keys từ file .env
load_dotenv()

# Cấu hình DeepSeek
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"
config["deep_think_llm"] = "deepseek-v4-pro"
config["quick_think_llm"] = "deepseek-v4-flash"
config["max_debate_rounds"] = 2
config["output_language"] = "Vietnamese"

# Sử dụng yfinance cho Vàng (thường ổn định hơn cho FX/Hàng hóa miễn phí)
config["data_vendors"] = {
    "core_stock_apis": "yfinance",
    "technical_indicators": "yfinance",
    "fundamental_data": "yfinance",
    "news_data": "yfinance",
}

# Khởi tạo Agent
print("--- HỘI ĐỒNG GIÀ LÀNG ĐANG SOI VÀNG XAUUSD (EXNESS STYLE) ---")
ta = TradingAgentsGraph(debug=True, config=config)

# Phân tích ngày gần nhất (Thứ 6, 01/05/2026)
ticker = "XAUUSD=X"
date = "2026-05-01"
print(f"Mã: {ticker} | Ngày phân tích: {date}")

try:
    _, decision = ta.propagate(ticker, date)
    print("\n" + "="*50)
    print("QUYẾT ĐỊNH CUỐI CÙNG:")
    print(decision)
    print("="*50)
except Exception as e:
    print(f"LỖI KHI ĐI SĂN: {e}")
    print("Có thể do dữ liệu ngày hôm nay chưa sẵn sàng hoặc API bị nghẽn. Thử lại với ngày cũ hơn 1 chút.")
