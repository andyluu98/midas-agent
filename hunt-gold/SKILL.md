---
name: hunt-gold
description: Phân tích và cung cấp tín hiệu giao dịch Vàng (XAUUSD) thời gian thực cho sàn Exness. Kết hợp sức mạnh của DeepSeek v4 Pro (vĩ mô), TradingView (kỹ thuật/tâm lý) và MT5 (giá chuẩn Exness). Sử dụng khi người dùng yêu cầu "soi vàng", "kèo exness", "phân tích vàng" hoặc bất kỳ câu hỏi nào về việc giao dịch vàng ngay lập tức.
---

# Hunt Gold Skill

Skill này giúp bạn trở thành thợ săn vàng thực thụ trên sàn Exness bằng cách hợp nhất 3 nguồn dữ liệu quan trọng nhất.

## Điều kiện tiên quyết

1.  **Ứng dụng MT5**: Phải đang mở ứng dụng MetaTrader 5 (Exness) trên máy tính.
2.  **Market Watch**: Mã Vàng (XAUUSD, GOLD, hoặc XAUUSDm) phải hiển thị trong bảng Market Watch (chuột phải chọn "Show All").
3.  **Python Environment**: Đã cài đặt đầy đủ `MetaTrader5`, `tradingview-ta`, và các thư viện trong `TradingAgents`.

## Quy trình thực hiện

Khi người dùng yêu cầu soi vàng, hãy thực hiện các bước sau:

1.  **Chạy script tối thượng**: Thực hiện lệnh `python ultimate_gold_hunter.py` tại thư mục gốc của dự án.
2.  **Đọc kết quả**: Script sẽ trả về phân tích từ Già làng DeepSeek kết hợp với giá thực tế từ MT5 và tín hiệu từ TradingView.
3.  **Trình bày cho người dùng**:
    - Hiển thị giá hiện tại trên Exness.
    - Tóm tắt nhận định của DeepSeek về vĩ mô.
    - Tóm tắt tín hiệu kỹ thuật khung M5/M15 từ TradingView.
    - **QUYẾT ĐỊNH CUỐI CÙNG**: MUA/BÁN/ĐỨNG NGOÀI kèm theo các mức **Entry, SL, TP** cụ thể.

## Lưu ý quan trọng

- Luôn nhắc người dùng rằng đây là phân tích của AI, họ cần tự chịu trách nhiệm với quyết định đầu tư của mình.
- Nếu MT5 báo lỗi kết nối, hãy yêu cầu người dùng kiểm tra xem app MT5 đã mở chưa.
- Mặc định sử dụng DeepSeek v4 Pro để có độ chính xác cao nhất.
