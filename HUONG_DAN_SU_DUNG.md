# 🏹 CẨM NANG THỢ SĂN VÀNG (ULTIMATE GOLD HUNTER V3)

Chào mừng Thủ lĩnh đã sở hữu Pháo đài săn Vàng tối thượng. Đây là hướng dẫn để vận hành bộ tộc Agent của bạn trên sàn Exness.

## 1. Cấu trúc Hang (Thư mục)
- `super_watcher.py`: **Vệ binh Tầng 1** (Chạy 24/7, Miễn phí). Soi 7 chỉ báo kỹ thuật + Volume MT5.
- `ultimate_gold_hunter.py`: **Hội đồng Già làng Tầng 2** (Chỉ chạy khi có kèo, Tốn token). Tổng hợp Vĩ mô, Tâm lý, Nhật ký và Quản trị rủi ro.
- `.env`: Nơi cất giữ "Lửa" (API Keys của DeepSeek và Alpha Vantage).
- `tradingview_provider.py` & `mt5_provider.py`: Các "Mắt thần" kết nối dữ liệu.

## 2. Cách Vận hành (Quy trình 3 bước)

### Bước 1: Mở mắt cho Vệ binh
- Mở ứng dụng **MetaTrader 5 (Exness)** trên máy tính.
- Đảm bảo tài khoản đã đăng nhập.
- Chuột phải vào bảng **Market Watch** chọn **"Show All"** để hiện mã XAUUSD.

### Bước 2: Cho Vệ binh canh cửa
Mở một Terminal (Dòng lệnh) và gõ:
```bash
python super_watcher.py
```
*Vệ binh sẽ nhảy số 30 giây/lần. Khi điểm > 80, nó sẽ tự gọi Già làng.*

### Bước 3: Nhận kèo từ Già làng
- Bạn có thể đợi Vệ binh hú, hoặc chủ động chat với Gemini: **"Soi vàng cho tôi"**.
- Già làng DeepSeek v4 Pro sẽ xuất bản bản tin có đầy đủ: **MUA/BÁN, ENTRY, STOP-LOSS, TAKE-PROFIT** và số **LOT** nên đánh.

## 3. Các tuyệt chiêu bổ sung
- **Soi nhanh (Không tốn tiền)**: `python scalp_gold.py` (Chỉ xem tín hiệu kỹ thuật thuần túy).
- **Kiểm tra kết nối**: `python check_mt5.py`.

## 4. Lưu ý của Già làng
- **Volume là chìa khóa**: Nếu giá chạy mạnh mà Volume báo "Thấp", tuyệt đối không đuổi theo.
- **Tin tức Fed**: Trước và sau tin Fed 30 phút, hãy rút hết thợ săn về hang (Ngừng trade).
- **Tài khoản Cent**: Hệ thống đã được tối ưu để đọc số dư USC của Exness.

---
*Chúc Thủ lĩnh đi săn đại thắng!*
