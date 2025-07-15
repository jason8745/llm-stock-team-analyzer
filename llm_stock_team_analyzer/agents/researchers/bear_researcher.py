from llm_stock_team_analyzer.utils.logger import get_logger


def create_bear_researcher(llm, memory):
    logger = get_logger(__name__)

    def bear_node(state) -> dict:
        logger.info("🐻 Bear Researcher started")

        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

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

        prompt = f"""您是一位看空分析師，負責反對投資該股票的論證。您的目標是提出理由充分的論點，強調風險、挑戰和負面指標。利用提供的研究和數據來突出潛在的不利因素並有效反駁看多論點。

重要：保持回應簡潔和重點突出（最多300字）。直接且有影響力。

重點關注要素：

- 風險和挑戰：強調可能阻礙股票表現的因素，如市場飽和、財務不穩定或宏觀經濟威脅。
- 競爭劣勢：強調弱點，如較弱的市場地位、創新衰退或來自競爭對手的威脅。
- 負面指標：使用財務數據、市場趨勢或近期不利新聞的證據來支持您的立場。
- 反駁看多觀點：用具體數據和合理推理批判性分析看多論點，揭露弱點或過度樂觀的假設。
- 互動參與：以對話風格呈現您的論點，直接與看多分析師的觀點互動並有效辯論，而不僅僅是列舉事實。

可用資源：

市場研究報告：{market_research_report}
最新世界事務新聞：{news_report}
辯論對話歷史：{history}
最後的看多論點：{current_response}
類似情況的反思和經驗教訓：{past_memory_str}

使用這些信息提供令人信服的看空論點，反駁看多的主張，並參與動態辯論，展示投資該股票的風險和弱點。您還必須處理反思並從過去的經驗教訓和錯誤中學習。

格式：提供重點突出、有力的中文回應，直接且切中要點。避免冗長的解釋。"""

        response = llm.invoke(prompt)

        argument = f"看空分析師：{response.content}"

        logger.info(f"   已產出看空論點 ({len(argument)} 字符)")

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state.get("count", 0) + 1,
            "bull_count": investment_debate_state.get("bull_count", 0),
            "bear_count": investment_debate_state.get("bear_count", 0) + 1,
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
                f"🐻 Bear Researcher created final investment plan ({len(investment_plan)} chars)"
            )

        logger.info("🐻 Bear Researcher finished")

        return result

    return bear_node
