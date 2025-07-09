import json
import time

from langchain_core.messages import AIMessage

from llm_stock_team_analyzer.utils.logger import get_logger


def create_bull_researcher(llm, memory):
    logger = get_logger(__name__)

    def bull_node(state) -> dict:
        logger.info("🐂 Bull Researcher started")

        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        news_report = state["news_report"]

        bull_count = investment_debate_state.get("bull_count", 0)
        bear_count = investment_debate_state.get("bear_count", 0)
        logger.info(
            f"   狀態：Bull({bull_count}) Bear({bear_count}) History({len(history)}字符)"
        )

        # More permissive history truncation to maintain rich context
        max_history_chars = 3500

        if len(history) > max_history_chars:
            # Keep recent complete exchanges with better logic
            truncated_history = history[-max_history_chars:]

            # Find the first complete analyst statement to avoid mid-sentence cuts
            lines = truncated_history.split("\n")
            for i, line in enumerate(lines):
                if (
                    line.startswith("看多分析師：")
                    or line.startswith("看空分析師：")
                    or line.startswith("Bull Analyst:")
                    or line.startswith("Bear Analyst:")
                ):
                    history = "\n".join(lines[i:])
                    break

            logger.info(f"   已截斷歷史至 {len(history)} 字符")

        curr_situation = f"{market_research_report}\n\n{news_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=1)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""您是一位看多分析師，負責為投資該股票提供支持論據。您的任務是建立強有力的、基於證據的論證，強調成長潛力、競爭優勢和積極的市場指標。利用提供的研究和數據來解決疑慮並有效反駁看空論點。

重要：保持回應簡潔和重點突出（最多300字）。直接且有影響力。

重點關注要素：
- 成長潛力：強調公司的市場機會、營收預測和擴展性。
- 競爭優勢：強調獨特產品、強大品牌或主導市場地位等因素。
- 積極指標：使用財務健康、行業趨勢和近期積極新聞作為證據。
- 反駁看空觀點：用具體數據和合理推理批判性分析看空論點，徹底解決疑慮並展示為什麼看多觀點具有更強的價值。
- 互動參與：以對話風格呈現您的論點，直接與看空分析師的觀點互動並有效辯論，而不僅僅是列舉數據。

可用資源：
市場研究報告：{market_research_report}
最新世界事務新聞：{news_report}
辯論對話歷史：{history}
最後的看空論點：{current_response}
類似情況的反思和經驗教訓：{past_memory_str}

使用這些信息提供令人信服的看多論點，反駁看空的疑慮，並參與動態辯論，展示看多立場的優勢。您還必須處理反思並從過去的經驗教訓和錯誤中學習。

格式：提供重點突出、有力的中文回應，直接且切中要點。避免冗長的解釋。"""

        response = llm.invoke(prompt)

        argument = f"看多分析師：{response.content}"

        logger.info(f"   已產出看多論點 ({len(argument)} 字符)")

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state.get("count", 0) + 1,
            "bull_count": investment_debate_state.get("bull_count", 0) + 1,
            "bear_count": investment_debate_state.get("bear_count", 0),
            "judge_decision": investment_debate_state.get("judge_decision", ""),
        }

        logger.info(
            f"   New bull count: {new_investment_debate_state.get('bull_count', 0)}"
        )
        logger.info(
            f"   New bear count: {new_investment_debate_state.get('bear_count', 0)}"
        )

        # Check if this is the final round and create investment plan
        max_rounds = 2  # Should match the config
        result = {"investment_debate_state": new_investment_debate_state}

        if (
            new_investment_debate_state.get("bull_count", 0) >= max_rounds
            and new_investment_debate_state.get("bear_count", 0) >= max_rounds
        ):
            debate_history = new_investment_debate_state.get("history", "")
            investment_plan = f"研究團隊多空攻防：\n{debate_history}"
            result["investment_plan"] = investment_plan
            logger.info(
                f"🐂 Bull Researcher created final investment plan ({len(investment_plan)} chars)"
            )

        logger.info("🐂 Bull Researcher finished")

        return result

    return bull_node
