from langchain_core.tools import tool
from typing import Annotated
from tradingagents.dataflows.interface import route_to_vendor
from tradingagents.dataflows.search_provider import search as _web_search


@tool
def search_web(
    query: Annotated[str, "Search query, e.g. 'XAUUSD gold news Fed CPI 24h'"],
    max_results: Annotated[int, "Max results to return"] = 8,
) -> str:
    """
    Search the web realtime via auto-fallback chain
    (Tavily > Anthropic web_search > Claude CLI > Gemini CLI).

    USE THIS instead of relying on training data when you need:
    - Recent news / events (last 24h-7d)
    - Live sentiment from social media
    - Macro data (Fed rates, CPI prints, oil prices)
    - Anything for commodity/forex (XAUUSD, XAGUSD) where Yahoo has no data.

    Args:
        query: Specific search query in English or Vietnamese.
        max_results: Max number of articles (default 8).

    Returns:
        str: Formatted search results with title, URL, date, summary per article.
    """
    resp = _web_search(query, max_results=max_results)
    return resp.format_for_llm()

@tool
def get_news(
    ticker: Annotated[str, "Ticker symbol"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Retrieve news data for a given ticker symbol.
    Uses the configured news_data vendor.
    Args:
        ticker (str): Ticker symbol
        start_date (str): Start date in yyyy-mm-dd format
        end_date (str): End date in yyyy-mm-dd format
    Returns:
        str: A formatted string containing news data
    """
    return route_to_vendor("get_news", ticker, start_date, end_date)

@tool
def get_global_news(
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "Number of days to look back"] = 7,
    limit: Annotated[int, "Maximum number of articles to return"] = 5,
) -> str:
    """
    Retrieve global news data.
    Uses the configured news_data vendor.
    Args:
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): Number of days to look back (default 7)
        limit (int): Maximum number of articles to return (default 5)
    Returns:
        str: A formatted string containing global news data
    """
    return route_to_vendor("get_global_news", curr_date, look_back_days, limit)

@tool
def get_insider_transactions(
    ticker: Annotated[str, "ticker symbol"],
) -> str:
    """
    Retrieve insider transaction information about a company.
    Uses the configured news_data vendor.
    Args:
        ticker (str): Ticker symbol of the company
    Returns:
        str: A report of insider transaction data
    """
    return route_to_vendor("get_insider_transactions", ticker)
