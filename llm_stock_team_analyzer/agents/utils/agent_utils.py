from typing import Annotated

from langchain_core.messages import HumanMessage, RemoveMessage
from langchain_core.tools import tool

import llm_stock_team_analyzer.dataflows.interface as interface
from llm_stock_team_analyzer.configs.config import get_config


def create_msg_delete():
    def delete_messages(state):
        """Clear messages and add placeholder for Anthropic compatibility"""
        messages = state["messages"]

        # Remove all messages
        removal_operations = [RemoveMessage(id=m.id) for m in messages]

        # Add a minimal placeholder message
        placeholder = HumanMessage(content="Continue")

        return {"messages": removal_operations + [placeholder]}

    return delete_messages


class Toolkit:
    _config = None

    @classmethod
    def update_config(cls, config):
        """Update the class-level configuration."""
        cls._config = config

    @property
    def config(self):
        """Access the configuration."""
        if self._config is None:
            self._config = get_config()
        return self._config

    def __init__(self, config=None):
        if config:
            self.update_config(config)
        elif self._config is None:
            self._config = get_config()

    @staticmethod
    @tool
    def get_YFin_data(
        symbol: Annotated[str, "ticker symbol of the company"],
        start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
        end_date: Annotated[str, "End date in yyyy-mm-dd format"],
    ) -> str:
        """
        Retrieve the stock price data for a given ticker symbol from Yahoo Finance.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            start_date (str): Start date in yyyy-mm-dd format
            end_date (str): End date in yyyy-mm-dd format
        Returns:
            str: A formatted dataframe containing the stock price data for the specified ticker symbol in the specified date range.
        """

        result_data = interface.get_stock_price_data(symbol, start_date, end_date)

        return result_data

    @staticmethod
    @tool
    def get_stockstats_indicators_report(
        symbol: Annotated[str, "ticker symbol of the company"],
        indicator: Annotated[
            str, "technical indicator to get the analysis and report of"
        ],
        curr_date: Annotated[
            str, "The current trading date you are trading on, YYYY-mm-dd"
        ],
        look_back_days: Annotated[int, "how many days to look back"] = 30,
    ) -> str:
        """
        Retrieve stock stats indicators for a given ticker symbol and indicator.
        IMPORTANT: This function accepts only ONE indicator per call. Call this function only once
        per analysis with your most important selected indicator.

        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM
            indicator (str): Technical indicator to get the analysis and report of (ONE indicator only)
            curr_date (str): The current trading date you are trading on, YYYY-mm-dd
            look_back_days (int): How many days to look back, default is 30
        Returns:
            str: A formatted dataframe containing the stock stats indicators for the specified ticker symbol and indicator.
        """

        result_stockstats = interface.get_stock_stats_indicators_window(
            symbol, indicator, curr_date, look_back_days, True
        )

        return result_stockstats

    @staticmethod
    @tool
    def get_google_news(
        query: Annotated[str, "Query to search with"],
        curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    ):
        """
        Retrieve the latest news from Google News based on a query and date range.
        Args:
            query (str): Query to search with
            curr_date (str): Current date in yyyy-mm-dd format
        Returns:
            str: A formatted string containing the latest news from Google News based on the query and date range.
        """

        google_news_results = interface.get_google_news(query, curr_date, 7)

        return google_news_results

    @staticmethod
    @tool
    def get_company_info(
        symbol: Annotated[str, "ticker symbol of the company"],
    ) -> str:
        """
        Retrieve basic company information for a given ticker symbol.
        Args:
            symbol (str): Ticker symbol of the company, e.g. AAPL, TSM, 3017.TW
        Returns:
            str: Company information including name, sector, industry, and other basic details.
        """
        try:
            stock_info = interface.get_company_info(symbol)
            return stock_info
        except Exception as e:
            return f"Error retrieving company info for {symbol}: {str(e)}"
