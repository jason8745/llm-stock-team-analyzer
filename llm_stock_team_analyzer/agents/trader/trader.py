import functools
import json
import time

from llm_stock_team_analyzer.utils.logger import get_logger


def create_trader(llm, memory):
    def trader_node(state, name):
        logger = get_logger()

        # Check investment plan availability
        investment_plan = state.get("investment_plan", "")
        logger.info(f"[TRADER] 已接收投資計劃 ({len(investment_plan)} 字符)")

        company_name = state["company_of_interest"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]

        curr_situation = f"{market_research_report}\n\n{news_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        context = {
            "role": "user",
            "content": f"基於分析師團隊的綜合分析，這是為{company_name}量身定制的投資計劃。該計劃結合了當前技術市場趨勢、宏觀經濟指標和社交媒體情緒的洞察。請將此計劃作為評估您下一個交易決策的基礎。\n\n建議投資計劃：{investment_plan}\n\n利用這些洞察做出明智和戰略性的決策。",
        }

        messages = [
            {
                "role": "system",
                "content": f"""您是一位交易代理，分析市場數據以做出投資決策。基於您的分析，提供具體的買入、賣出或持有建議。以堅定的決策結束，並始終以「最終交易建議：**買入/持有/賣出**」結束您的回應以確認您的建議。不要忘記利用過去決策的經驗教訓來從錯誤中學習。以下是您在類似情況下交易的一些反思和經驗教訓：{past_memory_str}。請用中文撰寫所有分析和建議。""",
            },
            context,
        ]

        result = llm.invoke(messages)

        # Log trader's decision with detailed information
        logger.info(f"🎯 [TRADER] 交易員分析完成")
        logger.info(f"[TRADER] 投資計劃總字數: {len(investment_plan)} 字符")
        logger.info(f"[TRADER] 交易決策內容長度: {len(result.content)} 字符")

        # Log trader decision in chunks to avoid truncation
        decision_content = result.content
        logger.info(f"[TRADER] 交易決策已完成 ({len(decision_content)} 字符)")

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "final_trade_decision": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
