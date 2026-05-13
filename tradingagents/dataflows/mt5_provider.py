import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime

def get_mt5_data(symbol="XAUUSD", timeframe=mt5.TIMEFRAME_M15, n_bars=100):
    """Lấy dữ liệu OHLC từ MT5."""
    if not mt5.initialize():
        return {"error": f"Khởi tạo thất bại: {mt5.last_error()}"}
    
    # Tìm mã chuẩn trên sàn
    symbols_to_try = [symbol, symbol+"c", symbol+"m", symbol+".e", "GOLD"]
    target_symbol = None
    for s in symbols_to_try:
        if mt5.symbol_select(s, True):
            target_symbol = s
            break
            
    if not target_symbol:
        return {"error": "Không tìm thấy mã Vàng trong Market Watch."}
    
    rates = mt5.copy_rates_from_pos(target_symbol, timeframe, 0, n_bars)
    if rates is None:
        return {"error": "Không lấy được dữ liệu nến."}
        
    df = pd.DataFrame(rates)
    df['time'] = pd.to_datetime(df['time'], unit='s')
    
    # Lấy volume trung bình để Agent so sánh
    avg_volume = df['tick_volume'].mean()
    last_volume = df['tick_volume'].iloc[-1]
    volume_status = "Cao" if last_volume > avg_volume * 1.5 else "Thấp" if last_volume < avg_volume * 0.5 else "Bình thường"
    
    tick = mt5.symbol_info_tick(target_symbol)
    
    return {
        "symbol": target_symbol,
        "current_bid": tick.bid,
        "current_ask": tick.ask,
        "df": df,
        "spread": (tick.ask - tick.bid),
        "last_volume": last_volume,
        "volume_status": volume_status
    }

def get_account_summary():
    """Lấy thông tin tài khoản."""
    if not mt5.initialize():
        return None
    acc = mt5.account_info()
    if acc:
        return {
            "balance": acc.balance,
            "equity": acc.equity,
            "margin_free": acc.margin_free,
            "currency": acc.currency
        }
    return None


# Mapping label → MT5 timeframe enum + giây/nến (để gen future timestamps)
TF_MAP = {
    "M5":  (mt5.TIMEFRAME_M5,  5 * 60),
    "M15": (mt5.TIMEFRAME_M15, 15 * 60),
    "H1":  (mt5.TIMEFRAME_H1,  60 * 60),
    "H4":  (mt5.TIMEFRAME_H4,  4 * 60 * 60),
    "D1":  (mt5.TIMEFRAME_D1,  24 * 60 * 60),
}


def get_ohlcv_dataframe(tf_label: str, lookback: int, symbol: str = "XAUUSD") -> pd.DataFrame:
    """Adapter cho Kronos: trả DataFrame có cột time/open/high/low/close/volume."""
    if not mt5.initialize():
        return pd.DataFrame()
    tf_enum, _ = TF_MAP[tf_label]

    # Tìm symbol thực tế trên sàn
    symbols_to_try = [symbol, symbol + "c", symbol + "m", symbol + ".e", "GOLD"]
    target = next((s for s in symbols_to_try if mt5.symbol_select(s, True)), None)
    if not target:
        return pd.DataFrame()

    rates = mt5.copy_rates_from_pos(target, tf_enum, 0, lookback)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()

    df = pd.DataFrame(rates)
    df["time"] = pd.to_datetime(df["time"], unit="s")
    df["volume"] = df["tick_volume"]
    return df[["time", "open", "high", "low", "close", "volume"]]


def get_future_timestamps(tf_label: str, pred_len: int) -> pd.Series:
    """Sinh chuỗi timestamp tương lai dựa trên thời gian hiện tại + interval của khung."""
    _, secs = TF_MAP[tf_label]
    now = pd.Timestamp.now().floor(f"{secs}s")
    future = pd.date_range(start=now + pd.Timedelta(seconds=secs), periods=pred_len, freq=f"{secs}s")
    return pd.Series(future)
