# Midas Agent — AI Trading Framework cho XAUUSD Scalp M15

**Midas Agent** dựng một "phòng họp 8 chuyên gia AI" trong máy bạn, chuyên trade vàng (XAUUSD) khung M15 trên MT5 Exness. Mỗi phiên ~90 giây, chi phí ~$0.20.

<div align="center">

⚡ [Cài đặt nhanh](#cài-đặt-nhanh)  |  🏹 [Săn vàng (Gold Hunter)](#săn-vàng--ultimate_gold_hunterpy)  |  ⚙️ [3 file cần biết](#3-file-bạn-cần-biết)  |  🔍 [Search backend](#search-backend-tự-động)  |  🛡️ [Cảnh báo rủi ro](#cảnh-báo-rủi-ro)

</div>

> ⚠️ **Midas Agent là công cụ NGHIÊN CỨU + HỖ TRỢ RA QUYẾT ĐỊNH.** Output là **tín hiệu tham khảo** — KHÔNG phải khuyến nghị đầu tư. Paper trade tối thiểu 2 tuần trước khi chạy live. AI có thể sai, thị trường có thể black-swan.

---

## 🎯 Vì sao Midas khác

| Tiêu chí | Trader tự đọc | ChatGPT thuần | Indicator Bot | **Midas Agent** |
|----------|:-:|:-:|:-:|:-:|
| Số góc nhìn | 1 | 1 | 1 | **8 góc** ✅ |
| Tranh luận đa vòng | ❌ | ❌ | ❌ | **✅ 2-4 vòng** |
| Bộ nhớ tự học | ❌ | ❌ | ❌ | **✅** |
| Ra SL/TP/Lot cụ thể | Tự tính | Mơ hồ | Cứng | **✅ Auto** |
| Hiểu tin tức + tâm lý | Thủ công | Không có data | ❌ | **✅ Realtime** |
| Chi phí | Thời gian | $20/tháng | $10-100/tháng | **$0.20/phiên** |

---

## 🏗️ Kiến trúc — 8 Agent + 4 Tầng

Mô phỏng cách các quỹ đầu cơ tỉ đô (Citadel, Renaissance) vận hành:

**Tầng 1 — Phân tích (4 chuyên viên song song)**
- **Fundamentals Analyst** — Macro (lãi suất Fed, CPI, USD index, GLD ETF flow)
- **Sentiment Analyst** — Twitter/Reddit gold sentiment
- **News Analyst** — Fed/CPI/NFP/FOMC + geopolitical
- **Technical Analyst** — RSI/MACD/Bollinger trên khung M15

**Tầng 2 — Tranh luận (2 vòng debate)**
- **Bull Researcher** ⚔️ **Bear Researcher** — cãi nhau bằng số liệu, chống AI ảo

**Tầng 3 — Trader**
- Đề xuất MUA/BÁN/ĐỨNG NGOÀI kèm Entry + SL + TP

**Tầng 4 — Rủi ro + Sếp**
- 3 Risk Debator (hung hăng / thận trọng / trung lập) → **Portfolio Manager** gõ búa cuối

---

## 🏹 Săn vàng — `ultimate_gold_hunter.py`

Script ĐẶC BIỆT cho trader vàng. Combo 3 tầng AI **chéo nhau** để giảm sai sót tối đa:

```
TẦNG 1 — KRONOS 🔦
  ML model dự báo 3 khung H1/M15/M5 cùng lúc
  M15 = khung CHÍNH (scalper), H1 nền, M5 xác nhận
  Bỏ H4 (24h quá xa cho scalp)

TẦNG 2 — TRADINGVIEW 👁️
  26 indicator vote → STRONG_BUY / BUY / NEUTRAL / SELL / STRONG_SELL
  Free API qua tradingview-ta

TẦNG 3 — DEEPSEEK COUNCIL 🧙
  8 agent + News + Sentiment + Memory + Risk debate
  → BẢN TIN CHIẾN THUẬT CUỐI CÙNG (MUA/BÁN/ĐỨNG NGOÀI + SL/TP/Lot)
```

**Tính năng bảo vệ trader:**
- ⏸️ **Gate skip M15 NEUTRAL** — Nếu Kronos M15 không rõ hướng, script DỪNG ngay, không gọi Council (tiết kiệm tiền + tránh vào lệnh xấu)
- 🛡️ **Cap SL 10 pip** — Auto ép SL ≤ 10 pip ($10) cho scalp M15, chống plan kiểu Daily lệch khung
- ⚠️ **Real account warning** — Nếu MT5 server có chữ "Real", script hỏi y/N trước khi chạy
- 💰 **Position sizer** — Tính lot Cent theo balance + Kronos consensus tier (A+/B/C), risk 1%/lệnh, max 5%/ngày

**Quy ước pip Cách A:** 1 pip XAUUSD = **$1 di chuyển** (giá $4670 → $4680 = 10 pip). SL bị cap tối đa 10 pip ($10) cho M15 scalp.

Chạy:
```bash
python ultimate_gold_hunter.py
```

Output mẫu:
```
🏹 BẢN TIN SĂN VÀNG — XAUUSDc 14/05/2026 06:00 ICT
═══════════════════════════════════════════════════
💰 Giá: $4,680.00  |  Balance: 11,400 USC  |  Max risk: $1.14

🔮 KRONOS 3 KHUNG → BUY (3/3 đồng thuận, Tier A+)
   H1  BUY  +0.30%  →  range=[4675, 4695]
   M15 BUY  +0.35%  →  range=[4677, 4690]  ← khung chính
   M5  BUY  +0.21%  →  range=[4679, 4685]

🛡️ TRADINGVIEW M15 → STRONG_BUY (18 mua / 3 bán / 5 trung lập)

🎯 PLAN:  MUA XAUUSDc @ $4,680  |  SL $4,673 (7 pip)  |  TP $4,690 (10 pip)
💰 LOT:   0.05 Cent  |  Risk $1.14  |  Multiplier 1.2x (Tier A+)
```

---

## 📦 Cài đặt nhanh

### Yêu cầu
- Windows 10/11 (Mac/Linux chạy được nhưng MT5 chính thức chỉ Windows)
- Python 3.13 (qua Miniconda)
- MT5 terminal đã đăng nhập demo hoặc real (khuyến nghị Exness Cent)
- Thẻ Visa/Master quốc tế để nạp DeepSeek

### Cài đặt
```bash
# 1. Clone repo
git clone https://github.com/andyluu98/midas-agent.git
cd midas-agent

# 2. Tạo môi trường conda
conda create -n midas python=3.13
conda activate midas

# 3. Cài tất cả dependencies
pip install .

# 4. Cài MetaTrader5 package cho Python
pip install MetaTrader5

# 5. Cấu hình .env
cp .env.example .env
# Mở .env, dán DEEPSEEK_API_KEY và TAVILY_API_KEY (optional)
```

### Verify cài đặt
```bash
tradingagents --help
```

---

## 🔑 API Keys

### Bắt buộc
- **DeepSeek API** — LLM chính (rẻ, tiếng Việt tốt). Đăng ký tại `platform.deepseek.com`. Top-up 10 USD ≈ 50 phiên.

### Khuyến nghị
- **Tavily API** — Search backend cho News/Sentiment/Fundamental analyst (chống AI bịa tin). Free 1000 search/tháng tại `tavily.com`.

### Optional
- **Alpha Vantage** — News fallback cho commodity
- **Anthropic** — Fallback search backend
- **OpenAI/Google/xAI/Qwen/GLM** — Provider thay thế DeepSeek

Đặt vào `.env`:
```bash
DEEPSEEK_API_KEY=sk-...
TAVILY_API_KEY=tvly-...           # optional but recommended
ALPHA_VANTAGE_API_KEY=...         # optional
```

---

## 🔍 Search Backend Tự Động

Để 3 analyst (News/Sentiment/Fundamental) **không bịa tin** trên XAUUSD (Yahoo không có data commodity), Midas tự động chọn search backend theo chain:

```
1. Tavily API     (tốt nhất — TAVILY_API_KEY trong .env)
2. Anthropic web_search native  (ANTHROPIC_API_KEY)
3. Claude CLI subprocess         (command `claude` available)
4. Gemini CLI subprocess         (command `gemini` available)
5. None — analyst chỉ dùng training data (cảnh báo nhẹ)
```

Khi chạy, script in backend đang dùng:
```
🔍 Search backend: TAVILY
```

---

## 🚀 Sử dụng

### Cách 1: Script Gold Hunter (khuyến nghị cho trader vàng)
```bash
python ultimate_gold_hunter.py
```

### Cách 2: CLI tổng quát (cho ticker khác)
```bash
tradingagents
# Interactive menu: chọn ticker, ngày, LLM provider, depth
```

### Cách 3: Python API
```python
from tradingagents.graph.trading_graph import TradingAgentsGraph
from tradingagents.default_config import DEFAULT_CONFIG

config = DEFAULT_CONFIG.copy()
config["llm_provider"] = "deepseek"
config["deep_think_llm"] = "deepseek-v4-pro"
config["quick_think_llm"] = "deepseek-v4-flash"
config["output_language"] = "Vietnamese"
config["max_debate_rounds"] = 2

ta = TradingAgentsGraph(debug=True, config=config)
_, decision = ta.propagate("XAUUSD", "2026-05-14")
print(decision)
```

---

## ⚙️ 3 File Bạn Cần Biết

| File | Mục đích |
|------|----------|
| **`.env`** | Giấu API key (DEEPSEEK_API_KEY, TAVILY_API_KEY...) |
| **`tradingagents/default_config.py`** | Điều chỉnh LLM provider, số vòng debate, output language |
| **`ultimate_gold_hunter.py`** | Script chạy chính cho trader vàng |

---

## 💾 Persistence & Recovery

### Memory tự học
Mỗi phiên ghi vào `~/.tradingagents/memory/trading_memory.md`. Phiên sau cùng ticker → AI nhớ lỗi cũ, đưa bài học vào prompt → hệ thống tự khôn theo thời gian.

### Checkpoint resume
Mất điện giữa phiên? Bật `--checkpoint`:
```bash
tradingagents analyze --checkpoint
```
Lần chạy lại resume đúng chỗ — không mất tiền API.

---

## 🛡️ Cảnh báo rủi ro

- ⚠️ **TÍN HIỆU THAM KHẢO** — không phải khuyến nghị đầu tư
- ⚠️ **PAPER TRADE 2 tuần** trước khi chạy live
- ⚠️ AI có thể sai, thị trường có thể black-swan
- ⚠️ Quản lý vốn ≤ 1-2% mỗi lệnh, max 5%/ngày (code đã enforce)
- ⚠️ KHÔNG đặt lệnh trực tiếp từ output — luôn xác nhận bằng mắt + biểu đồ
- ⚠️ Khi MT5 dùng tài khoản REAL, script cảnh báo + hỏi y/N

---

## 🙏 Credit & License

Midas Agent là **fork tuỳ biến** của [TauricResearch/TradingAgents](https://github.com/TauricResearch/TradingAgents) (MIT License) — chuyên hoá cho:

- ✅ XAUUSD scalp M15 trên MT5 Exness
- ✅ DeepSeek LLM (giá rẻ, tiếng Việt tốt) thay vì OpenAI o1
- ✅ Kronos ML forecaster đa khung
- ✅ TradingView free signal
- ✅ Position sizer cho Cent account
- ✅ Search backend auto-fallback (Tavily/Anthropic/CLI)
- ✅ Gate skip M15 NEUTRAL + cap SL 10 pip
- ✅ Real account warning
- ✅ Output tiếng Việt

Khung framework gốc (LangGraph multi-agent debate) thuộc TauricResearch. Mọi tuỳ biến trên đây thuộc Midas Agent contributors.

---

## 🤝 Contributing

Welcome bug fix, doc improvement, feature mới. Khuyến nghị mở issue trước khi PR. Past contributions credited per release in [`CHANGELOG.md`](CHANGELOG.md).

---

## 📚 Khóa học CES — AI Agent for Trading: Zero to Hero

7 video × 10 phút dạy trader VN không code dùng Midas từ đầu đến cuối:

- V0: Kiến trúc Midas (lecture)
- V1: Cài Python + Git + VS Code
- V2: Clone repo + conda + pip install
- V3: DeepSeek API + Tavily + .env
- V4: MT5 + lấy data XAUUSD
- V5: Chạy CLI 8 agent
- V6: Gold Hunter realtime (đặt SL/TP/Lot)

Đào tạo bởi **CES Global**.
