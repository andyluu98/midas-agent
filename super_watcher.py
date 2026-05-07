import MetaTrader5 as mt5
import pandas as pd
import time
from datetime import datetime
from tradingview_ta import TA_Handler, Interval
from tradingagents.dataflows.mt5_provider import get_mt5_data, get_account_summary
from tradingagents.dataflows.price_action import (
    detect_candlestick_pattern,
    bollinger_squeeze_score,
)

# Cấu hình 9 vũ khí kỹ thuật + Volume + Price Action
SYMBOL = "XAUUSD"
TIMEFRAME_MT5 = mt5.TIMEFRAME_M5
TIMEFRAME_TV = "5m"
N_BARS = 60  # đủ cho BB 20-period quantile

def get_technical_score(symbol):
    """Chấm điểm kỹ thuật dựa trên 7 vũ khí bạn chọn."""
    handler = TA_Handler(
        symbol="XAUUSD",
        screener="cfd",
        exchange="OANDA",
        interval=Interval.INTERVAL_5_MINUTES
    )
    
    try:
        analysis = handler.get_analysis()
        summary = analysis.summary
        indicators = analysis.indicators
        
        score = 0
        reasons = []

        # 1. Supertrend & EMA Ribbon (13, 21, 50) - Xác định xu hướng (40đ)
        # (TradingView TA tổng hợp các tín hiệu này vào summary)
        if summary['RECOMMENDATION'] == "STRONG_BUY":
            score += 40
            reasons.append("Xu hướng tăng cực mạnh (Supertrend + EMA Ribbon)")
        elif summary['RECOMMENDATION'] == "BUY":
            score += 25
            reasons.append("Xu hướng tăng (Thuận chiều)")
        elif summary['RECOMMENDATION'] == "STRONG_SELL":
            score += 40
            reasons.append("Xu hướng giảm cực mạnh (Supertrend + EMA Ribbon)")
        elif summary['RECOMMENDATION'] == "SELL":
            score += 25
            reasons.append("Xu hướng giảm (Thuận chiều)")

        # 2. Bollinger Bands & RSI & MACD - Nhịp thở & Cản (30đ)
        rsi = indicators.get('RSI', 50)
        if rsi < 30: 
            score += 15
            reasons.append(f"RSI Quá bán ({rsi:.1f}) - Cơ hội hồi phục")
        elif rsi > 70:
            score += 15
            reasons.append(f"RSI Quá mua ({rsi:.1f}) - Cơ hội đảo chiều")
            
        macd = indicators.get('MACD.macd', 0)
        signal = indicators.get('MACD.signal', 0)
        if (macd > signal and macd < 0) or (macd < signal and macd > 0):
            score += 15
            reasons.append("MACD đang hội tụ/phân kỳ - Sắp có biến")

        # 3. Donchian Channels & EMA Cross - Điểm nổ (20đ)
        # TradingView dùng EMA10/20 và đỉnh/đáy để tính phá vỡ
        if summary['BUY'] > 15 or summary['SELL'] > 15:
            score += 20
            reasons.append("Nhiều chỉ báo cùng đồng thuận - Điểm nổ xác nhận")

        return score, summary['RECOMMENDATION'], reasons
    except Exception as e:
        return 0, "ERROR", [str(e)]

def run_watcher():
    print("="*50)
    print("🛡️ SIÊU VỆ BINH GÁC HANG (SUPER WATCHER V3) 🛡️")
    print("Đang canh gác 7 vũ khí + Volume MT5...")
    print("="*50)
    
    if not mt5.initialize():
        print("❌ Lỗi: Phải mở app MT5 trước!")
        return

    while True:
        # 1. Lấy Volume & Giá từ MT5
        mt5_data = get_mt5_data(SYMBOL, TIMEFRAME_MT5, N_BARS)
        if "error" in mt5_data:
            print(f"Lỗi MT5: {mt5_data['error']}")
            time.sleep(10)
            continue

        price = mt5_data['current_bid']
        v_status = mt5_data['volume_status']
        v_val = mt5_data['last_volume']
        df = mt5_data['df']

        # 2. Lấy điểm kỹ thuật từ TradingView
        score, rec, reasons = get_technical_score(SYMBOL)

        # 3. Búa xác nhận Volume (10đ)
        if v_status == "Cao":
            score += 10
            reasons.append(f"Volume bùng nổ ({v_val}) - Cá mập ra quân")

        # 4. Vũ khí thứ 8: Candlestick pattern (15đ) — chỉ cộng nếu cùng chiều với rec
        pattern_name, pattern_dir = detect_candlestick_pattern(df.tail(3))
        if pattern_name:
            same_side = (pattern_dir == "BUY" and "BUY" in rec) or \
                        (pattern_dir == "SELL" and "SELL" in rec)
            if same_side:
                score += 15
                reasons.append(f"{pattern_name} thuận chiều - confirmation")
            else:
                reasons.append(f"{pattern_name} ngược chiều - cảnh báo đảo")

        # 5. Vũ khí thứ 9: Bollinger Squeeze (10đ) — sắp có cú nổ
        is_squeeze, bw = bollinger_squeeze_score(df)
        if is_squeeze:
            score += 10
            reasons.append(f"BB siết chặt (bw={bw:.4f}) - sắp nổ breakout")

        # 6. Hiển thị Dashboard
        now = datetime.now().strftime("%H:%M:%S")
        color = "\033[92m" if "BUY" in rec else "\033[91m" if "SELL" in rec else "\033[93m"
        reset = "\033[0m"
        
        print(f"[{now}] GIÁ: {price} | VOL: {v_val} ({v_status}) | ĐIỂM: {score}/125")
        print(f"TRẠNG THÁI: {color}{rec}{reset}")
        if reasons:
            print(f"LÝ DO: {' | '.join(reasons[-3:])}")

        if score >= 80:
            print("🔥 KÈO THƠM! Đang hỏi đèn pha tương lai (Kronos)...")
            # TẦNG 0: Kronos đa khung gate
            from tradingagents.dataflows.kronos_provider import multi_timeframe_forecast
            from tradingagents.dataflows.mt5_provider import get_ohlcv_dataframe, get_future_timestamps

            consensus = multi_timeframe_forecast(
                fetch_ohlcv=get_ohlcv_dataframe,
                fetch_future_ts=get_future_timestamps,
            )
            print("\n" + consensus.summary())

            # Gate: chỉ gọi DeepSeek nếu Kronos consensus đủ mạnh
            watcher_dir = "BUY" if "BUY" in rec else "SELL" if "SELL" in rec else "NEUTRAL"
            kronos_aligned = consensus.direction == watcher_dir and consensus.lot_multiplier > 0

            if kronos_aligned:
                print(f"\n✅ Kronos {consensus.confidence_tier} đồng thuận với Vệ binh — TRIỆU TẬP HỘI ĐỒNG DEEPSEEK")
                import subprocess
                subprocess.run(["python", "ultimate_gold_hunter.py"])
            else:
                print(f"\n⚠️  Kronos KHÔNG đồng thuận với Vệ binh ({consensus.direction} vs {watcher_dir}) — BỎ QUA, tiết kiệm token")

            print("-" * 50)
            time.sleep(300)  # Nghỉ 5 phút sau khi đánh giá kèo

        time.sleep(30)  # 30 giây soi một lần

if __name__ == "__main__":
    run_watcher()
