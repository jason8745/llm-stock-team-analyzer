import json
import time

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def create_market_analyst(llm, toolkit):
    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        # Use available tools only
        tools = [
            toolkit.get_YFin_data,
            toolkit.get_stockstats_indicators_report,
        ]

        system_message = """You are a trading assistant tasked with analyzing financial markets. Your role is to select the **most relevant indicator** for the given market condition or trading strategy from the following list.

IMPORTANT WORKFLOW INSTRUCTIONS:
1. Call get_YFin_data ONLY ONCE to retrieve the CSV data needed for indicators
2. Call get_stockstats_indicators_report ONLY ONCE with your SINGLE most important selected indicator
3. The get_stockstats_indicators_report function accepts only ONE indicator per call - choose the most relevant one
4. After receiving tool results, analyze the data and write your final comprehensive report
5. Do NOT make multiple calls to the same tool - each tool provides all the data you need in one call

Available indicators (choose ONE that best fits the analysis):

Moving Averages:
- close_50_sma: 50 SMA: A medium-term trend indicator. Usage: Identify trend direction and serve as dynamic support/resistance. Tips: It lags price; combine with faster indicators for timely signals.
- close_200_sma: 200 SMA: A long-term trend benchmark. Usage: Confirm overall market trend and identify golden/death cross setups. Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries.
- close_10_ema: 10 EMA: A responsive short-term average. Usage: Capture quick shifts in momentum and potential entry points. Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals.

MACD Related:
- macd: MACD: Computes momentum via differences of EMAs. Usage: Look for crossovers and divergence as signals of trend changes. Tips: Confirm with other indicators in low-volatility or sideways markets.
- macds: MACD Signal: An EMA smoothing of the MACD line. Usage: Use crossovers with the MACD line to trigger trades. Tips: Should be part of a broader strategy to avoid false positives.
- macdh: MACD Histogram: Shows the gap between the MACD line and its signal. Usage: Visualize momentum strength and spot divergence early. Tips: Can be volatile; complement with additional filters in fast-moving markets.

Momentum Indicators:
- rsi: RSI: Measures momentum to flag overbought/oversold conditions. Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis.

Volatility Indicators:
- boll: Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. Usage: Acts as a dynamic benchmark for price movement. Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals.
- boll_ub: Bollinger Upper Band: Typically 2 standard deviations above the middle line. Usage: Signals potential overbought conditions and breakout zones. Tips: Confirm signals with other tools; prices may ride the band in strong trends.
- boll_lb: Bollinger Lower Band: Typically 2 standard deviations below the middle line. Usage: Indicates potential oversold conditions. Tips: Use additional analysis to avoid false reversal signals.
- atr: ATR: Averages true range to measure volatility. Usage: Set stop-loss levels and adjust position sizes based on current market volatility. Tips: It's a reactive measure, so use it as part of a broader risk management strategy.

Volume-Based Indicators:
- vwma: VWMA: A moving average weighted by volume. Usage: Confirm trends by integrating price action with volume data. Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses.

Analysis Guidelines:
- Select the ONE indicator that provides the most relevant insight for the current market condition
- Briefly explain why your chosen indicator is most suitable for the given market context
- When calling get_stockstats_indicators_report, use the exact indicator name as listed above
- Write a very detailed and nuanced report based on the stock data and your chosen indicator
- Provide detailed and fine-grained analysis and insights that may help traders make decisions
- Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " IMPORTANT: Each tool should be called ONLY ONCE during your analysis."
                    " First call get_YFin_data, then call get_stockstats_indicators_report with your chosen indicator (one indicator only)."
                    " After receiving tool results, write your comprehensive final report - do NOT call tools again."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. The company we want to look at is {ticker}",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)

        result = chain.invoke(state["messages"])

        # If there are tool calls, let the tool node handle them
        # If no tool calls, this means the analyst has completed analysis
        if result.tool_calls:
            return {"messages": [result]}
        else:
            # No tool calls means analysis is complete
            return {
                "messages": [result],
                "market_report": result.content,
            }

    return market_analyst_node
