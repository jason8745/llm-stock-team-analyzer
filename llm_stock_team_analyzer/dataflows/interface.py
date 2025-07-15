"""
Interface module for stock market data retrieval and analysis.

This module provides clean, stateless functions for:
- Google News scraping
- Stock data retrieval via yfinance
- Technical indicator calculations

All functions are designed to be robust, testable, and suitable for offline operation.
"""

from datetime import datetime
from typing import Annotated

import pandas as pd
from dateutil.relativedelta import relativedelta

# Import our local modules
from .googlenews_utils import getNewsData
from .indicators import (
    calculate_adx,
    calculate_atr,
    calculate_bollinger_bands,
    calculate_kdj,
    calculate_macd,
    calculate_obv,
    calculate_rsi,
)
from .yfinance_utils import YFinanceService


def get_google_news(
    query: Annotated[
        str,
        "Search query for Google News (e.g., 'AAPL Apple stock'). Use company ticker and name for best results. ONE CALL retrieves ALL relevant news for the query and date range.",
    ],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[
        int,
        "Number of days to look back from curr_date (typically 7-14 days is sufficient for comprehensive news coverage)",
    ],
) -> str:
    """
    Retrieve comprehensive Google News data for a specific query and date range.

    IMPORTANT: This function returns ALL available news articles for the given query and date range
    in a SINGLE CALL. Do NOT call this function multiple times with the same parameters as it will
    return the same results. If you need different news topics, use different search queries.

    Args:
        query: Search query string. For stock analysis, use format like "AAPL Apple stock" or "company_name earnings"
        curr_date: End date for news search in YYYY-MM-DD format
        look_back_days: Days to look back (7-14 days typically provides comprehensive coverage)

    Returns:
        Formatted string containing ALL news articles found for the query and date range.
        Returns empty string if no news found. Each article includes title, source, and snippet.

    Usage Tips:
        - ONE call per unique query/date combination is sufficient
        - Use specific, relevant search terms for better results
        - 7-14 days lookback typically provides comprehensive news coverage
        - Do NOT make multiple calls with identical parameters
    """
    query = query.replace(" ", "+")

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    news_results = getNewsData(query, before, curr_date)

    news_str = ""

    for news in news_results:
        news_str += (
            f"### {news['title']} (source: {news['source']}) \n\n{news['snippet']}\n\n"
        )

    if len(news_results) == 0:
        return ""

    return f"## {query} Google News, from {before} to {curr_date}:\n\n{news_str}"


def get_stock_stats_indicators_window(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
    look_back_days: Annotated[int, "how many days to look back"],
    online: Annotated[bool, "to fetch data online or offline (both use yfinance)"],
) -> str:
    """
    Calculate and return technical indicators for a stock over a specified time window.

    Args:
        symbol: Stock ticker symbol
        indicator: Technical indicator name (see supported indicators below)
        curr_date: Current date in YYYY-mm-dd format
        look_back_days: Number of days to look back
        online: Whether to use online mode (both modes use yfinance for robustness)

    Returns:
        Formatted string with indicator values and description
    """

    # Supported indicators with descriptions
    supported_indicators = {
        # Moving Averages (優化參數版本)
        "close_5_ema": (
            "5 EMA: 超短線趨勢追蹤。"
            "用途：順勢追價時作為動態支撐阻力和進場退場參考。"
            "提示：極為敏感，需配合中長期均線過濾假訊號。"
        ),
        "close_10_ema": (
            "10 EMA: 短期趨勢動量指標。"
            "用途：捕捉價格動量變化和短線進場時機。"
            "提示：震盪市場易產生噪音，與長期均線配合使用。"
        ),
        "close_20_sma": (
            "20 SMA: 中短期趨勢基準。"
            "用途：取代50ma作為更敏感的中期趨勢判斷。"
            "提示：平衡敏感度與穩定性，適合快速市場。"
        ),
        "close_50_sma": (
            "50 SMA: 中期趨勢指標。"
            "用途：識別趨勢方向並作為動態支撐/阻力。"
            "提示：滯後於價格，適合趨勢確認。"
        ),
        "close_200_sma": (
            "200 SMA: 長期趨勢基準。"
            "用途：確認整體市場趨勢並識別黃金交叉/死亡交叉設置。"
            "提示：反應緩慢；最適合戰略趨勢確認而非頻繁交易進入。"
        ),
        # MACD Related (優化參數)
        "macd": (
            "MACD標準版(12,26,9)：經典動量指標。"
            "用途：尋找交叉和背離作為趨勢變化信號。"
            "提示：適合背離分析。"
        ),
        "macd_5_13_9": (
            "MACD快速版(5,13,9)：敏感動量指標。"
            "用途：提早捕捉動量轉變和進場訊號。"
            "提示：訊號更多但需要更嚴格過濾。"
        ),
        "macds": (
            "MACD信號線：MACD線的EMA平滑。"
            "用途：使用與MACD線的交叉來觸發交易。"
            "提示：應成為更廣泛策略的一部分。"
        ),
        "macdh": (
            "MACD柱狀圖：顯示MACD線與信號線之間的差距。"
            "用途：可視化動量強度。"
            "提示：較為波動，需要額外過濾。"
        ),
        # Momentum Indicators (優化參數)
        "rsi": (
            "RSI標準版(14期)：經典動量指標。"
            "用途：應用70/30閾值並觀察背離。"
            "提示：在強趨勢中可能保持極值。"
        ),
        "rsi_7": (
            "RSI快速版(7期)：超敏感超買超賣指標。"
            "用途：快速判斷極端點(>80/<20)和短線反轉機會。"
            "提示：訊號頻繁，需配合其他指標確認。"
        ),
        # Bollinger Bands (多參數版本)
        "boll": (
            "布林帶中線：作為布林帶的基礎。"
            "用途：作為價格運動的動態基準。"
            "提示：與上下軌結合使用以有效發現突破或反轉。"
        ),
        "boll_10_1.5": (
            "布林帶快速版(10期,1.5倍標準差)：敏感盤整突破指標。"
            "用途：更快速抓住盤整壓縮和突破時機。"
            "提示：訊號較多，適合短線操作。"
        ),
        "boll_20_2": (
            "布林帶標準版(20期,2倍標準差)：經典價格通道。"
            "用途：標準風險控制和突破確認。"
            "提示：較為穩定，適合中線操作。"
        ),
        "boll_ub": (
            "布林帶上軌：中線上方標準差軌道。"
            "用途：超買條件和突破區域判斷。"
            "提示：與其他工具確認信號；在強趨勢中價格可能沿著軌道運行。"
        ),
        "boll_lb": (
            "布林帶下軌：中線下方標準差軌道。"
            "用途：超賣條件判斷。"
            "提示：使用額外分析以避免虛假反轉信號。"
        ),
        # KDJ指標
        "kdj": (
            "KDJ隨機指標(9期)：標準超買超賣轉折指標。"
            "用途：轉折訊號，適合震盪突破判斷。"
            "提示：K>80超買，K<20超賣，注意金叉死叉。"
        ),
        "kdj_5": (
            "KDJ隨機指標(5期)：快速超買超賣轉折指標。"
            "用途：比標準KDJ更敏感的轉折訊號，適合震盪突破判斷。"
            "提示：K>80超買，K<20超賣，注意金叉死叉。"
        ),
        # Volatility Indicators (優化參數)
        "atr": (
            "ATR標準版(14期)：經典波動性測量。"
            "用途：根據當前市場波動性設置止損水平。"
            "提示：較為穩定的風險測量。"
        ),
        "atr_10": (
            "ATR快速版(10期)：敏感波動測量指標。"
            "用途：更快反應市場波動變化，適合動態止損設定。"
            "提示：對高波動市場反應更快。"
        ),
        # Volume-Based Indicators
        "vwma": (
            "VWMA：按成交量加權的移動平均線。"
            "用途：通過整合價格行為與成交量數據來確認趨勢。"
            "提示：注意成交量突增導致的偏斜。"
        ),
        "obv": (
            "OBV成交量平衡指標：量價關係分析。"
            "用途：偵測成交量與價格的背離現象，確認趨勢真實性。"
            "提示：量價背離常預示趨勢轉折。"
        ),
        # Trend Strength Indicators
        "adx": (
            "ADX平均趨勢指標：趨勢強度測量。"
            "用途：判斷市場是否處於趨勢狀態(>25強趨勢，<20盤整)。"
            "提示：不顯示方向只顯示強度。"
        ),
        "mfi": (
            "MFI: The Money Flow Index is a momentum indicator that uses both price and volume to measure buying and selling pressure. "
            "Usage: Identify overbought (>80) or oversold (<20) conditions and confirm the strength of trends or reversals. "
            "Tips: Use alongside RSI or MACD to confirm signals; divergence between price and MFI can indicate potential reversals."
        ),
    }

    if indicator not in supported_indicators:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(supported_indicators.keys())}"
        )

    try:
        # Calculate the start date based on look_back_days (add extra days for indicator calculation)
        end_date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
        start_date_obj = end_date_obj - relativedelta(days=look_back_days + 60)
        start_date = start_date_obj.strftime("%Y-%m-%d")

        # Get stock data using our yfinance utilities
        stock_data = YFinanceService.get_stock_data(symbol, start_date, curr_date)

        if stock_data is None or stock_data.empty:
            return f"No data available for {symbol} in the specified date range."

        # Standardize column names to lowercase for consistent access
        stock_data.columns = stock_data.columns.str.lower()

        # Remove timezone info from index for cleaner datetime operations
        if stock_data.index.tz is not None:
            stock_data.index = stock_data.index.tz_localize(None)

        # Calculate the technical indicator
        data_with_indicator = _calculate_indicator(stock_data.copy(), indicator)

        if data_with_indicator is None:
            return f"Failed to calculate indicator {indicator}"

        # Filter to the requested date range for display
        display_start = end_date_obj - relativedelta(days=look_back_days)
        display_data = data_with_indicator[data_with_indicator.index >= display_start]

        # Format the results
        result_lines = []
        for date, row in display_data.iterrows():
            date_str = date.strftime("%Y-%m-%d")
            indicator_values = _get_indicator_values(row, indicator)
            result_lines.append(f"{date_str}: {indicator_values}")

        result_str = (
            f"## {indicator} values from {display_start.strftime('%Y-%m-%d')} to {curr_date}:\n\n"
            + "\n".join(result_lines)
            + "\n\n"
            + supported_indicators.get(indicator, "No description available.")
        )

        return result_str

    except Exception as e:
        return f"Error calculating indicator {indicator} for {symbol}: {str(e)}"


def _calculate_indicator(data: pd.DataFrame, indicator: str) -> pd.DataFrame:
    """Calculate the specified technical indicator using our indicators.py functions"""
    try:
        # Moving Averages (優化參數版本)
        if indicator == "close_5_ema":
            data["close_5_ema"] = data["close"].ewm(span=5, adjust=False).mean()

        elif indicator == "close_10_ema":
            data["close_10_ema"] = data["close"].ewm(span=10, adjust=False).mean()

        elif indicator == "close_20_sma":
            data["close_20_sma"] = data["close"].rolling(window=20).mean()

        elif indicator == "close_50_sma":
            data["close_50_sma"] = data["close"].rolling(window=50).mean()

        elif indicator == "close_200_sma":
            data["close_200_sma"] = data["close"].rolling(window=200).mean()

        # MACD Related (優化參數)
        elif indicator == "macd":
            data = calculate_macd(data)  # 使用預設參數 (12,26,9)

        elif indicator == "macd_5_13_9":
            data = calculate_macd(data, short_period=5, long_period=13, signal_period=9)
            # 重新命名以區分不同參數版本
            data["macd_5_13_9"] = data["macd"]
            data["signal_5_13_9"] = data["signal_line"]

        elif indicator in ["macds", "macdh"]:
            data = calculate_macd(data)
            if indicator == "macdh":
                data["macdh"] = data["macd"] - data["signal_line"]

        # RSI (優化參數)
        elif indicator == "rsi":
            data = calculate_rsi(data, window=14)  # 標準版

        elif indicator == "rsi_7":
            data = calculate_rsi(data, window=7)  # 快速版
            data["rsi_7"] = data["rsi"]

        # Bollinger Bands (多參數版本)
        elif indicator == "boll":
            data = calculate_bollinger_bands(data, window=20, num_std_dev=2)

        elif indicator == "boll_10_1.5":
            data = calculate_bollinger_bands(data, window=10, num_std_dev=1.5)
            # 重新命名以區分不同參數版本
            data["boll_10_1.5_middle"] = data["bollinger_middle"]
            data["boll_10_1.5_upper"] = data["bollinger_upper"]
            data["boll_10_1.5_lower"] = data["bollinger_lower"]

        elif indicator == "boll_20_2":
            data = calculate_bollinger_bands(data, window=20, num_std_dev=2)
            # 重新命名以區分不同參數版本
            data["boll_20_2_middle"] = data["bollinger_middle"]
            data["boll_20_2_upper"] = data["bollinger_upper"]
            data["boll_20_2_lower"] = data["bollinger_lower"]

        elif indicator in ["boll_ub", "boll_lb"]:
            data = calculate_bollinger_bands(data)

        # KDJ指標
        elif indicator == "kdj":
            data = calculate_kdj(data, window=9)  # 標準版

        elif indicator == "kdj_5":
            data = calculate_kdj(data, window=5)  # 快速版
            # 重新命名以區分不同參數版本
            data["kdj_5_k"] = data["kdj_k"]
            data["kdj_5_d"] = data["kdj_d"]
            data["kdj_5_j"] = data["kdj_j"]

        # ATR (優化參數)
        elif indicator == "atr":
            data = calculate_atr(data, window=14)  # 標準版

        elif indicator == "atr_10":
            data = calculate_atr(data, window=10)  # 快速版
            data["atr_10"] = data["atr"]

        # Volume-Based Indicators
        elif indicator == "vwma":
            # Calculate VWMA (Volume Weighted Moving Average)
            window = 20
            data["vwma"] = (data["close"] * data["volume"]).rolling(
                window=window
            ).sum() / data["volume"].rolling(window=window).sum()

        elif indicator == "obv":
            data = calculate_obv(data)

        # Trend Strength Indicators
        elif indicator == "adx":
            data = calculate_adx(data, window=14)

        elif indicator == "mfi":
            # Calculate Money Flow Index (basic implementation)
            typical_price = (data["high"] + data["low"] + data["close"]) / 3
            money_flow = typical_price * data["volume"]

            # Positive and negative money flow
            positive_flow = (
                money_flow.where(typical_price > typical_price.shift(1), 0)
                .rolling(window=14)
                .sum()
            )
            negative_flow = (
                money_flow.where(typical_price < typical_price.shift(1), 0)
                .rolling(window=14)
                .sum()
            )

            money_ratio = positive_flow / negative_flow
            data["mfi"] = 100 - (100 / (1 + money_ratio))

        return data

    except Exception as e:
        print(f"Error calculating indicator {indicator}: {e}")
        return None


def _get_indicator_values(row: pd.Series, indicator: str) -> str:
    """Extract and format the indicator values from a data row"""
    try:
        # Moving Averages
        if indicator == "close_5_ema":
            value = row.get("close_5_ema", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "close_10_ema":
            value = row.get("close_10_ema", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "close_20_sma":
            value = row.get("close_20_sma", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "close_50_sma":
            value = row.get("close_50_sma", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "close_200_sma":
            value = row.get("close_200_sma", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        # MACD Related
        elif indicator == "macd":
            macd_val = row.get("macd", "N/A")
            signal_val = row.get("signal_line", "N/A")
            if pd.notna(macd_val) and pd.notna(signal_val):
                return f"MACD: {macd_val:.4f}, Signal: {signal_val:.4f}"
            return "N/A"

        elif indicator == "macd_5_13_9":
            macd_val = row.get("macd_5_13_9", "N/A")
            signal_val = row.get("signal_5_13_9", "N/A")
            if pd.notna(macd_val) and pd.notna(signal_val):
                return f"MACD(5,13,9): {macd_val:.4f}, Signal: {signal_val:.4f}"
            return "N/A"

        elif indicator == "macds":
            signal_val = row.get("signal_line", "N/A")
            return f"{signal_val:.4f}" if pd.notna(signal_val) else "N/A"

        elif indicator == "macdh":
            macdh_val = row.get("macdh", "N/A")
            return f"{macdh_val:.4f}" if pd.notna(macdh_val) else "N/A"

        # RSI
        elif indicator == "rsi":
            rsi_val = row.get("rsi", "N/A")
            return f"{rsi_val:.2f}" if pd.notna(rsi_val) else "N/A"

        elif indicator == "rsi_7":
            rsi_val = row.get("rsi_7", "N/A")
            return f"{rsi_val:.2f}" if pd.notna(rsi_val) else "N/A"

        # Bollinger Bands
        elif indicator == "boll":
            value = row.get("bollinger_middle", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "boll_10_1.5":
            middle = row.get("boll_10_1.5_middle", "N/A")
            upper = row.get("boll_10_1.5_upper", "N/A")
            lower = row.get("boll_10_1.5_lower", "N/A")
            if all(pd.notna(val) for val in [middle, upper, lower]):
                return f"Middle: {middle:.2f}, Upper: {upper:.2f}, Lower: {lower:.2f}"
            return "N/A"

        elif indicator == "boll_20_2":
            middle = row.get("boll_20_2_middle", "N/A")
            upper = row.get("boll_20_2_upper", "N/A")
            lower = row.get("boll_20_2_lower", "N/A")
            if all(pd.notna(val) for val in [middle, upper, lower]):
                return f"Middle: {middle:.2f}, Upper: {upper:.2f}, Lower: {lower:.2f}"
            return "N/A"

        elif indicator == "boll_ub":
            value = row.get("bollinger_upper", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "boll_lb":
            value = row.get("bollinger_lower", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        # KDJ
        elif indicator == "kdj":
            k_val = row.get("kdj_k", "N/A")
            d_val = row.get("kdj_d", "N/A")
            j_val = row.get("kdj_j", "N/A")
            if all(pd.notna(val) for val in [k_val, d_val, j_val]):
                return f"K: {k_val:.2f}, D: {d_val:.2f}, J: {j_val:.2f}"
            return "N/A"

        elif indicator == "kdj_5":
            k_val = row.get("kdj_5_k", "N/A")
            d_val = row.get("kdj_5_d", "N/A")
            j_val = row.get("kdj_5_j", "N/A")
            if all(pd.notna(val) for val in [k_val, d_val, j_val]):
                return f"K: {k_val:.2f}, D: {d_val:.2f}, J: {j_val:.2f}"
            return "N/A"

        # ATR
        elif indicator == "atr":
            value = row.get("atr", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "atr_10":
            value = row.get("atr_10", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        # Volume-Based
        elif indicator == "vwma":
            value = row.get("vwma", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "obv":
            value = row.get("obv", "N/A")
            return f"{value:.0f}" if pd.notna(value) else "N/A"

        # Trend Strength
        elif indicator == "adx":
            value = row.get("adx", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        elif indicator == "mfi":
            value = row.get("mfi", "N/A")
            return f"{value:.2f}" if pd.notna(value) else "N/A"

        return "N/A"

    except Exception:
        return "N/A"


def get_stock_price_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    """
    Get stock price data for the specified symbol and date range.

    Args:
        symbol: Stock ticker symbol
        start_date: Start date in YYYY-mm-dd format
        end_date: End date in YYYY-mm-dd format

    Returns:
        Formatted string with stock price data
    """
    try:
        # Validate date formats
        datetime.strptime(start_date, "%Y-%m-%d")
        datetime.strptime(end_date, "%Y-%m-%d")

        # Get stock data using our yfinance utilities
        data = YFinanceService.get_stock_data(symbol, start_date, end_date)

        # Check if data is empty
        if data is None or data.empty:
            return f"No data found for symbol '{symbol}' between {start_date} and {end_date}"

        # Standardize column names to lowercase for consistent access
        data.columns = data.columns.str.lower()

        # Remove timezone info from index for cleaner output
        if data.index.tz is not None:
            data.index = data.index.tz_localize(None)

        # Round numerical values to 2 decimal places for cleaner display
        numeric_columns = ["open", "high", "low", "close", "adj_close"]
        for col in numeric_columns:
            if col in data.columns:
                data[col] = data[col].round(2)

        # Convert DataFrame to CSV string
        csv_string = data.to_csv()

        # Add header information
        header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
        header += f"# Total records: {len(data)}\n"
        header += (
            f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        )

        return header + csv_string

    except Exception as e:
        return f"Error retrieving data for {symbol}: {str(e)}"


def get_company_info(symbol: str) -> str:
    """
    Get basic company information for the specified symbol.

    Args:
        symbol: Stock ticker symbol

    Returns:
        Formatted string with company information
    """
    try:
        # Get company info using our yfinance utilities
        stock_info = YFinanceService.get_stock_info(symbol)

        # Format the company information
        info_lines = [
            f"# Company Information for {symbol.upper()}",
            f"Company Name: {stock_info.short_name or 'N/A'}",
            f"Sector: {stock_info.sector or 'N/A'}",
            f"Industry: {stock_info.industry or 'N/A'}",
            f"Country: {stock_info.country or 'N/A'}",
        ]

        if stock_info.market_cap:
            info_lines.append(f"Market Cap: ${stock_info.market_cap:,.0f}")

        if stock_info.pe_ratio:
            info_lines.append(f"P/E Ratio: {stock_info.pe_ratio:.2f}")

        if stock_info.website:
            info_lines.append(f"Website: {stock_info.website}")

        return "\n".join(info_lines)

    except Exception as e:
        return f"Error retrieving company info for {symbol}: {str(e)}"
