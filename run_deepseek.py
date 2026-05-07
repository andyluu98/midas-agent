from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG
from dotenv import load_dotenv
import os

# Nạp API keys từ file .env
load_dotenv()

# Cấu hình sử dụng DeepSeek model cao nhất theo tài liệu mới nhất
config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"
config["deep_think_llm"] = "deepseek-v4-pro"  # Model mạnh nhất người dùng chọn
config["quick_think_llm"] = "deepseek-v4-flash" # Model nhanh để làm việc nhỏ
config["max_debate_rounds"] = 2  # Tăng số vòng tranh luận để có kết quả tốt hơn
config["output_language"] = "Vietnamese" # Xuất kết quả bằng tiếng Việt

# Sử dụng Alpha Vantage cho dữ liệu chất lượng cao
config["data_vendors"] = {
    "core_stock_apis": "alpha_vantage",
    "technical_indicators": "alpha_vantage",
    "fundamental_data": "alpha_vantage",
    "news_data": "alpha_vantage",
}

# Khởi tạo và chạy Agent cho mã NVDA (Nvidia)
print("--- ĐANG TRIỂN KHAI ĐỘI QUÂN AGENT VỚI NÃO BỘ DEEPSEEK V4 PRO ---")
ta = TradingAgentsGraph(debug=True, config=config)

# Chạy phân tích cho ngày gần đây (ví dụ 2024-05-15 hoặc ngày bạn muốn)
ticker = "NVDA"
date = "2024-05-15"
print(f"Săn mồi mã: {ticker} vào ngày: {date}")

_, decision = ta.propagate(ticker, date)

print("\n--- QUYẾT ĐỊNH CUỐI CÙNG TỪ GIÀ LÀNG ---")
print(decision)
