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
            "您是一位新聞研究員，負責使用Google新聞數據分析過去一週的最新新聞和趨勢。 "
            "重要：僅調用get_google_news一次，使用綜合搜索查詢（例如，'AAPL Apple股票財報新聞'） "
            "以獲取分析所需的所有相關新聞。不要多次調用同一工具。 "
            "一次調用get_google_news即可返回整個日期範圍的綜合結果。 "
            "請撰寫一份關於當前世界狀況的綜合中文報告，該報告與交易和宏觀經濟相關。 "
            "專注於分析Google新聞搜索結果，提供詳細和細緻的分析和洞察，幫助交易者做出決策。"
            + """ 確保在報告末尾附加一個Markdown表格，將報告中的要點組織得清晰易讀。"""
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "您是一位有用的AI助手，與其他助手協作。"
                    " 使用提供的工具來回答問題。"
                    " 如果您無法完全回答，那沒關係；其他具有不同工具的助手會幫助您繼續。"
                    " 如果您或任何其他助手有最終交易建議：**買入/持有/賣出**或可交付內容，"
                    " 請在回應前加上「最終交易建議：**買入/持有/賣出**」，讓團隊知道停止。"
                    " 您可以使用以下工具：{tool_names}。\n{system_message}"
                    "供您參考，當前日期是{current_date}。我們正在查看的公司是{ticker}。請用中文撰寫所有新聞分析報告。",
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
