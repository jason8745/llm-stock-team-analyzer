import json
import time

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Use only available news tools
        tools = [toolkit.get_google_news]

        system_message = (
            "You are a news researcher tasked with analyzing recent news and trends over the past week using Google News data. "
            "IMPORTANT: Call get_google_news ONLY ONCE with a comprehensive search query (e.g., 'AAPL Apple stock earnings news') "
            "that will retrieve ALL relevant news for your analysis. Do NOT make multiple calls to the same tool. "
            "One call to get_google_news returns comprehensive results for the entire date range. "
            "Please write a comprehensive report of the current state of the world that is relevant for trading and macroeconomics. "
            "Focus on analyzing the Google News search results to provide detailed and fine-grained analysis and insights that may help traders make decisions."
            + """ Make sure to append a Markdown table at the end of the report to organize key points in the report, organized and easy to read."""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You are a helpful AI assistant, collaborating with other assistants."
                    " Use the provided tools to progress towards answering the question."
                    " If you are unable to fully answer, that's OK; another assistant with different tools"
                    " will help where you left off. Execute what you can to make progress."
                    " If you or any other assistant has the FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** or deliverable,"
                    " prefix your response with FINAL TRANSACTION PROPOSAL: **BUY/HOLD/SELL** so the team knows to stop."
                    " You have access to the following tools: {tool_names}.\n{system_message}"
                    "For your reference, the current date is {current_date}. We are looking at the company {ticker}",
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
                "news_report": result.content,
            }

    return news_analyst_node
