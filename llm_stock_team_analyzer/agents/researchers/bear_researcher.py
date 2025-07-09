import json
import time

from langchain_core.messages import AIMessage


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        news_report = state["news_report"]

        # Truncate history to prevent token overflow - keep only last 2 exchanges
        history_lines = history.strip().split("\n") if history else []
        if len(history_lines) > 4:  # Keep last 4 lines (2 bull + 2 bear responses)
            history = "\n".join(history_lines[-4:])

        curr_situation = f"{market_research_report}\n\n{news_report}"
        past_memories = memory.get_memories(
            curr_situation, n_matches=1
        )  # Reduced from 2 to 1

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""You are a Bear Analyst making the case against investing in the stock. Your goal is to present a well-reasoned argument emphasizing risks, challenges, and negative indicators. Leverage the provided research and data to highlight potential downsides and counter bullish arguments effectively.

IMPORTANT: Keep your response CONCISE and focused (maximum 300 words). Be direct and impactful.

Key points to focus on:

- Risks and Challenges: Highlight factors like market saturation, financial instability, or macroeconomic threats that could hinder the stock's performance.
- Competitive Weaknesses: Emphasize vulnerabilities such as weaker market positioning, declining innovation, or threats from competitors.
- Negative Indicators: Use evidence from financial data, market trends, or recent adverse news to support your position.
- Bull Counterpoints: Critically analyze the bull argument with specific data and sound reasoning, exposing weaknesses or over-optimistic assumptions.
- Engagement: Present your argument in a conversational style, directly engaging with the bull analyst's points and debating effectively rather than simply listing facts.

Resources available:

Market research report: {market_research_report}
Latest world affairs news: {news_report}
Conversation history of the debate: {history}
Last bull argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}

Use this information to deliver a compelling bear argument, refute the bull's claims, and engage in a dynamic debate that demonstrates the risks and weaknesses of investing in the stock. You must also address reflections and learn from lessons and mistakes you made in the past.

FORMAT: Provide a focused, punchy response that is direct and to the point. Avoid lengthy explanations."""

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

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

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
