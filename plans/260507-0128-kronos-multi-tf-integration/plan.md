# Kronos Multi-Timeframe Integration

**Created:** 2026-05-07 01:28 ICT
**Completed:** 2026-05-07 01:50 ICT
**Branch:** main
**Status:** ✅ DONE — tested with synthetic data, ready for live MT5

## Goal
Tích hợp Kronos foundation model vào hệ thống săn vàng XAUUSD Exness để có "đèn pha tương lai" — dự báo OHLCV cho 4 khung giờ song song, làm filter trước khi gọi DeepSeek council.

## User Profile
- Trade: vài lệnh/ngày, không canh máy liên tục
- Entry timeframe: **M15**
- Bias timeframes: H4 (trend lớn), H1 (confirm)

## Architecture (3 tầng AI)

```
TẦNG 0: Kronos forecast (NEW)
   ├─ H4 lookback=400, predict=6 nến (24h)   → BIAS LỚN
   ├─ H1 lookback=400, predict=12 nến (12h)  → CONFIRM
   ├─ M15 lookback=400, predict=16 nến (4h)  → ENTRY/SL/TP ⭐
   └─ M5 lookback=400, predict=12 nến (1h)   → TIMING (REMOVABLE*)
   ↓ run parallel via threading, total ~3-4s
TẦNG 1: super_watcher (existing)
   ↓ score >= 80 → trigger Tier 0+2
TẦNG 2: ultimate_gold_hunter (existing)
   ↓ Kronos forecast injected into DeepSeek prompt
TẦNG 3: position_sizer (NEW)
   ↓ lot_size dựa trên Kronos confidence + balance Exness
```

\* **M5 REMOVABLE** — user yêu cầu giữ tạm, sẽ bỏ sau khi quen hệ thống. Set
   `KRONOS_TIMEFRAMES = ["H4", "H1", "M15", "M5"]` → để bỏ chỉ cần xóa "M5".

## Combination rules

| Khung cùng chiều | Action |
|---|---|
| 4/4 | Setup A+ → full lot |
| 3/4 | Setup B → nửa lot |
| ≤ 2 | NO TRADE — bỏ qua |

## Files created ✅

- `tradingagents/dataflows/kronos_vendor/` — vendored Kronos model code (3 files từ shiyu-coder/Kronos)
- `tradingagents/dataflows/kronos_provider.py` — singleton wrapper + multi-TF parallel forecast (~250 lines)
- `tradingagents/dataflows/position_sizer.py` — Tier 3 lot calculator (~140 lines)

## Files modified ✅

- `tradingagents/dataflows/mt5_provider.py` — thêm `get_ohlcv_dataframe()` + `get_future_timestamps()` adapter cho Kronos
- `super_watcher.py` — gate Kronos consensus trước khi gọi hunter
- `ultimate_gold_hunter.py` — Tier 0 (Kronos) + Tier 3 (position sizer) integrated, prompt DeepSeek nhận forecast

## Test results

| Test | Result |
|---|---|
| Kronos load | ✅ 7.4s lần đầu (download model + tokenizer) |
| Single TF predict | ✅ 2.3s trên CPU |
| 4 TF parallel (M5/M15/H1/H4) | ✅ 9s tổng (serialize predict, race fix bằng `_predict_lock`) |
| Position sizer A+/B/cap/SL gần | ✅ 5/5 cases pass |

## Race condition fix

KronosPredictor có internal state — không thread-safe. Đã thêm `threading.Lock()` quanh `predict()` call. Inference serialize, fetch data parallel.

## Open questions (đang hỏi user)

- [x] Câu 1: Khung giờ — **chọn 4 khung (H4/H1/M15/M5), M5 sẽ bỏ sau**
- [x] Câu 2: Model size — **Kronos-small (24M params, ~100MB)**, có thể nâng base sau
- [x] Câu 3: Trigger mode — **A. On-demand** (chỉ chạy khi watcher score ≥ 80)
- [x] Câu 4: Position sizing — **B. Balanced (1% risk/trade)**, balance ~11,000 USC (~$110 USD real)

## Position Sizer Config (Tier 3)

```python
RISK_PER_TRADE = 0.01           # 1% balance/lệnh
MAX_TRADES_PER_DAY = 5
MAX_DAILY_RISK = 0.05           # 5% balance/ngày
ACCOUNT_TYPE = "exness_cent"    # 1 lot Cent = 0.01 standard

# Multipliers theo Kronos consensus
KRONOS_MULTIPLIER = {
    4: 1.2,   # 4/4 khung cùng chiều → boost
    3: 1.0,   # 3/4 → full lot
    2: 0.5,   # 2/4 → nửa lot
    1: 0.0,   # ≤1 → KHÔNG VÀO
    0: 0.0,
}
```

Với balance ~11,000 USC (~$110 USD):
- 1 lệnh: rủi ro ~$1.10 = 110 USC
- SL gold M15 ~50-100 pips → lot ~1-2 Cent (0.01-0.02 standard)

## Removal note (M5)

Khi bỏ M5 sau này:
1. Xóa `"M5"` khỏi `KRONOS_TIMEFRAMES` trong `kronos_provider.py`
2. Cập nhật combination rule: 3/3, 2/3, ≤1 thay vì 4/4, 3/4, ≤2
3. ~3-4s → 2-3s latency

## Future option: scheduled mode (B)

Nếu sau này muốn chuyển từ A (on-demand) → B (định kỳ + on-demand):
1. Tạo `kronos_scheduler.py` chạy cron 15 phút/lần
2. Cache forecast vào `~/.tradingagents/cache/kronos_latest.json` với TTL 15 phút
3. `super_watcher` đọc cache thay vì chờ inference → có thể dùng forecast vào điểm số rule-based
4. Cost: 4 khung × 96 lần/ngày = 384 inference/ngày (CPU chạy nền liên tục)
5. Lợi: watcher chấm điểm có "outlook" thật, không phụ thuộc threshold cứng 80đ

## Upgrade note (small → base)

Khi muốn nâng lên Kronos-base (chính xác hơn, chậm hơn):
1. Đổi `MODEL_NAME = "NeoQuasar/Kronos-small"` → `"NeoQuasar/Kronos-base"` trong `kronos_provider.py`
2. Lần đầu chạy sẽ tự tải ~400MB (1 lần duy nhất)
3. Latency 4 khung song song: ~3-4s → ~10-12s — vẫn OK vì chỉ gọi on-demand
