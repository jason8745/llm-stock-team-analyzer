from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        # Add company info tool to get correct company name
        tools = [toolkit.get_company_info, toolkit.get_google_news]

        system_message = (
            "您是一位專業金融新聞研究員，請嚴格遵循以下分析流程：\n"
            "\n【步驟一：獲取公司資訊】\n"
            "請先呼叫 get_company_info 工具，取得正確的英文公司名稱與基本資料。\n"
            "\n【步驟二：新聞搜尋】\n"
            "僅能呼叫一次 get_google_news 工具，並且必須使用英文公司名稱進行搜尋，絕不能翻譯成中文。\n"
            "搜尋語句格式範例：\n"
            "- AAPL：'AAPL Apple Inc stock news earnings'\n"
            "- MSFT：'MSFT Microsoft Corporation stock news earnings'\n"
            "- 3017.TW：'3017.TW Asia Vital Components stock news earnings'\n"
            "- 2330.TW：'2330.TW Taiwan Semiconductor stock news earnings'\n"
            "- NVDA：'NVDA NVIDIA Corporation stock news earnings'\n"
            "\n【報告撰寫要求】\n"
            "請以中文撰寫一份結構化的新聞分析報告，嚴格按照以下六個部分：\n"
            "\n## 1. 公司要聞摘要\n"
            "簡要整理本週公司相關的重大新聞事件。\n"
            "\n## 2. 所屬產業趨勢\n"
            "分析該公司所屬產業的最新發展動態與趨勢。\n"
            "\n## 3. 總體經濟影響\n"
            "評估新聞事件對總體經濟可能造成的影響。\n"
            "\n## 4. 重點新聞整理表\n"
            "以 Markdown 表格格式呈現，包含：新聞標題、日期、來源、分類（利多/利空/中性）。\n"
            "\n## 5. 新聞分類與理由\n"
            "針對每則重要新聞，詳細說明其分類理由與對股價的潛在影響。\n"
            "\n## 6. 綜合交易觀點\n"
            "根據所有新聞分析，給出整體交易建議（偏多/偏空/趨勢不明），並提供具體理由。\n"
            "\n請確保報告內容專業、客觀，並以實際交易決策為導向。"
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
