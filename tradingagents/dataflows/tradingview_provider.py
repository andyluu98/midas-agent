import tradingview_ta
from tradingview_ta import TA_Handler, Interval, Exchange
from typing import Annotated
import datetime

def get_tradingview_analysis_report(
    symbol: Annotated[str, "ticker symbol (e.g., NVDA, XAUUSD)"],
    interval: Annotated[str, "timeframe: 1m, 5m, 15m, 1h, 1d"] = "1h"
) -> str:
    """
    Lấy phân tích kỹ thuật thời gian thực từ TradingView.
    Cung cấp các tín hiệu Mua/Bán dựa trên hàng chục chỉ báo kỹ thuật.
    """
    tv_intervals = {
        "1m": Interval.INTERVAL_1_MINUTE,
        "5m": Interval.INTERVAL_5_MINUTES,
        "15m": Interval.INTERVAL_15_MINUTES,
        "30m": Interval.INTERVAL_30_MINUTES,
        "1h": Interval.INTERVAL_1_HOUR,
        "2h": Interval.INTERVAL_2_HOURS,
        "4h": Interval.INTERVAL_4_HOURS,
        "1d": Interval.INTERVAL_1_DAY,
    }
    
    # Chuẩn hóa mã
    clean_symbol = symbol.split('=')[0].upper()
    
    # Tự động chọn exchange và screener
    exchange = "OANDA"
    screener = "cfd"
    
    if clean_symbol in ["XAUUSD", "GOLD"]:
        tv_symbol = "XAUUSD"
        exchange = "OANDA"
        screener = "cfd"
    elif clean_symbol in ["BTCUSD", "ETHUSD", "SOLUSD"]:
        tv_symbol = clean_symbol
        exchange = "BINANCE"
        screener = "crypto"
    else:
        # Mặc định coi là cổ phiếu US
        tv_symbol = clean_symbol
        exchange = "NASDAQ" # Hoặc NYSE tùy mã, tradingview-ta thường tự tìm được nếu để trống hoặc sai nhẹ
        screener = "america"

    handler = TA_Handler(
        symbol=tv_symbol,
        exchange=exchange,
        screener=screener,
        interval=tv_intervals.get(interval, Interval.INTERVAL_1_HOUR)
    )
    
    try:
        analysis = handler.get_analysis()
        summary = analysis.summary
        indicators = analysis.indicators
        
        report = f"## BÁO CÁO KỸ THUẬT REAL-TIME (TRADINGVIEW) - {tv_symbol}\n"
        report += f"Khung thời gian: {interval} | Cập nhật lúc: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        report += f"### TỔNG KẾT: **{summary['RECOMMENDATION']}**\n"
        report += f"- MUA: {summary['BUY']}\n"
        report += f"- BÁN: {summary['SELL']}\n"
        report += f"- TRUNG LẬP: {summary['NEUTRAL']}\n\n"
        
        def fmt(key: str, decimals: int = 2) -> str:
            v = indicators.get(key)
            if isinstance(v, (int, float)):
                return f"{v:.{decimals}f}"
            return "N/A"

        report += "### CHỈ BÁO QUAN TRỌNG:\n"
        report += f"- RSI (14): {fmt('RSI')}\n"
        report += f"- MACD Level: {fmt('MACD.macd')}\n"
        report += f"- ADX (20): {fmt('ADX')}\n"
        report += f"- Bollinger Upper: {fmt('BB.upper')}\n"
        report += f"- Bollinger Lower: {fmt('BB.lower')}\n"
        report += f"- VOLUME: {indicators.get('volume', 'N/A')}\n"
        report += f"- MFI (Money Flow): {fmt('MFI')}\n"
        report += f"- VWAP: {fmt('VWAP')}\n"

        return report
    except Exception as e:
        return f"Lỗi khi lấy dữ liệu TradingView cho {symbol}: {str(e)}"

if __name__ == "__main__":
    print(get_tradingview_analysis_report("XAUUSD", "15m"))
