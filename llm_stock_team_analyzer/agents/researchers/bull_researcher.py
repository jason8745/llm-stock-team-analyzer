import json
import time

from langchain_core.messages import AIMessage


def create_bull_researcher(llm, memory):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

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

        prompt = f"""You are a Bull Analyst advocating for investing in the stock. Your task is to build a strong, evidence-based case emphasizing growth potential, competitive advantages, and positive market indicators. Leverage the provided research and data to address concerns and counter bearish arguments effectively.

IMPORTANT: Keep your response CONCISE and focused (maximum 300 words). Be direct and impactful.

Key points to focus on:
- Growth Potential: Highlight the company's market opportunities, revenue projections, and scalability.
- Competitive Advantages: Emphasize factors like unique products, strong branding, or dominant market positioning.
- Positive Indicators: Use financial health, industry trends, and recent positive news as evidence.
- Bear Counterpoints: Critically analyze the bear argument with specific data and sound reasoning, addressing concerns thoroughly and showing why the bull perspective holds stronger merit.
- Engagement: Present your argument in a conversational style, engaging directly with the bear analyst's points and debating effectively rather than just listing data.

Resources available:
Market research report: {market_research_report}
Latest world affairs news: {news_report}
Conversation history of the debate: {history}
Last bear argument: {current_response}
Reflections from similar situations and lessons learned: {past_memory_str}

Use this information to deliver a compelling bull argument, refute the bear's concerns, and engage in a dynamic debate that demonstrates the strengths of the bull position. You must also address reflections and learn from lessons and mistakes you made in the past.

FORMAT: Provide a focused, punchy response that is direct and to the point. Avoid lengthy explanations."""

        response = llm.invoke(prompt)

        argument = f"Bull Analyst: {response.content}"

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

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
