from tradingview_ta import TA_Handler, Interval

TV_INTERVALS = {
    "5m": Interval.INTERVAL_5_MINUTES,
    "15m": Interval.INTERVAL_15_MINUTES,
    "1h": Interval.INTERVAL_1_HOUR,
}


def check_gold_scalping():
    print("--- KIỂM TRA TÍN HIỆU VÀNG REAL-TIME CHO EXNESS ---")

    for interval_label, interval in TV_INTERVALS.items():
        print(f"\nĐang soi khung {interval_label}...")
        try:
            handler = TA_Handler(
                symbol="XAUUSD",
                exchange="OANDA",
                screener="cfd",
                interval=interval,
            )
            summary = handler.get_analysis().summary
        except Exception as e:
            print(f"Lỗi khung {interval_label}: {e}")
            continue

        rec = summary["RECOMMENDATION"]
        v_rec = "ĐỨNG NGOÀI"
        if "STRONG_BUY" in rec:
            v_rec = "🔥 MUA MẠNH"
        elif "BUY" in rec:
            v_rec = "✅ MUA"
        elif "STRONG_SELL" in rec:
            v_rec = "💀 BÁN MẠNH"
        elif "SELL" in rec:
            v_rec = "❌ BÁN"

        print(f"Kết luận: {v_rec}")
        print(
            f"Chi tiết: Mua({summary['BUY']}) | "
            f"Bán({summary['SELL']}) | Trung lập({summary['NEUTRAL']})"
        )


if __name__ == "__main__":
    check_gold_scalping()
