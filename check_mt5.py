import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def check_mt5_connection():
    print("--- ĐANG KIỂM TRA KẾT NỐI METATRADER 5 ---")
    
    # Khởi tạo kết nối tới app MT5
    if not mt5.initialize():
        print("KHÔNG THỂ KHỞI TẠO MT5. Hãy chắc chắn bạn đã mở app MT5 trên máy tính!")
        print(f"Lỗi: {mt5.last_error()}")
        return False
        
    # Lấy thông tin tài khoản
    account_info = mt5.account_info()
    if account_info is not None:
        print(f"Kết nối thành công!")
        print(f"Tài khoản: {account_info.login}")
        print(f"Sàn: {account_info.company}")
        print(f"Số dư: {account_info.balance} {account_info.currency}")
    else:
        print("Đã kết nối app nhưng chưa đăng nhập tài khoản!")
        
    # Thử lấy giá Vàng (XAUUSD)
    symbol = "XAUUSD"
    # Thử các tên phổ biến nếu XAUUSD không có (tùy sàn đặt tên)
    symbols_to_try = [symbol, "GOLD", "XAUUSDm", "XAUUSD.e"]
    
    found_symbol = None
    for s in symbols_to_try:
        selected = mt5.symbol_select(s, True)
        if selected:
            found_symbol = s
            break
            
    if found_symbol:
        tick = mt5.symbol_info_tick(found_symbol)
        print(f"\nGiá Vàng ({found_symbol}) hiện tại trên MT5:")
        print(f"Bid: {tick.bid} | Ask: {tick.ask}")
    else:
        print(f"\nKhông tìm thấy mã Vàng trong danh sách Market Watch của bạn.")
        print("Hãy chuột phải vào Market Watch và chọn 'Show All'.")

    # Đừng tắt để Agent còn dùng sau này
    # mt5.shutdown()
    return True

if __name__ == "__main__":
    check_mt5_connection()
