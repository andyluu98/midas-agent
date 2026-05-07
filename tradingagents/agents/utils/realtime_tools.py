from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor

def get_realtime_analysis(
    symbol: Annotated[str, "ticker symbol (e.g., NVDA, XAUUSD)"],
    interval: Annotated[str, "timeframe: 5m, 15m, 1h, 1d"] = "1h"
) -> str:
    """Get real-time technical analysis and buy/sell signals from TradingView."""
    return route_to_vendor("get_realtime_analysis", symbol, interval)
