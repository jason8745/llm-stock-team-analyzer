# LLM Stock Team Analyzer/graph/conditional_logic.py

from llm_stock_team_analyzer.agents.utils.agent_states import AgentState


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, selected_analysts=None):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.selected_analysts = selected_analysts or ["market", "news"]

    def should_continue_market(self, state: AgentState):
        """Determine if market analysis should continue."""
        messages = state["messages"]
        if not messages:
            # First run - should not happen with proper initialization
            return "Msg Clear Market"

        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            print(
                f"ℹ️  Market analyst triggered tools: {[tc.get('name', 'unknown') for tc in last_message.tool_calls]}"
            )
            return "tools_market"
        return "Msg Clear Market"

    def are_analysts_complete(self, state: AgentState) -> bool:
        """Check if all required analysts have completed their analysis."""
        completed_analysts = set()

        # Check which analysts have completed based on their reports
        if "market" in self.selected_analysts and state.get("market_report"):
            completed_analysts.add("market")
        if "news" in self.selected_analysts and state.get("news_report"):
            completed_analysts.add("news")

        required_analysts = set(self.selected_analysts)
        return completed_analysts == required_analysts

    def check_analysis_phase_complete(self, state: AgentState) -> str:
        """Check if analysis phase is complete and should transition to debate."""
        if not hasattr(state, "_analysis_complete_announced"):
            if self.are_analysts_complete(state):
                # Mark that analysis is complete to prevent repeated announcements
                state["_analysis_complete_announced"] = True
                state["_phase"] = "debate"
                return "analysis_complete"
        return "continue_analysis"

    def should_continue_news(self, state: AgentState):
        """Determine if news analysis should continue."""
        messages = state["messages"]
        if not messages:
            # First run - should not happen with proper initialization
            return "Msg Clear News"

        last_message = messages[-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            print(
                f"ℹ️  News analyst triggered tools: {[tc.get('name', 'unknown') for tc in last_message.tool_calls]}"
            )
            return "tools_news"
        return "Msg Clear News"

    def should_continue_debate(self, state: AgentState) -> str:
        """Determine if debate should continue."""
        # Initialize debate state if not present
        if "investment_debate_state" not in state:
            state["investment_debate_state"] = {
                "count": 0,
                "bull_count": 0,
                "bear_count": 0,
                "history": "",
                "bull_history": "",
                "bear_history": "",
                "current_response": "",
                "judge_decision": "",
            }

        debate_state = state["investment_debate_state"]

        # Enhanced safety checks to prevent infinite loops
        max_total_rounds = self.max_debate_rounds * 4  # Safety buffer
        max_individual_rounds = (
            self.max_debate_rounds * 2
        )  # Extra safety per researcher

        # Force end if too many total rounds
        if debate_state.get("count", 0) >= max_total_rounds:
            if "investment_plan" not in state or not state["investment_plan"]:
                debate_history = debate_state.get("history", "")
                state["investment_plan"] = (
                    f"Research Team Consensus (Max rounds reached):\n{debate_history}"
                )
            print(
                f"⚠️  Warning: Debate exceeded maximum total rounds ({max_total_rounds})"
            )
            return "Trader"

        # Force end if any researcher exceeded individual limit
        if (
            debate_state.get("bull_count", 0) >= max_individual_rounds
            or debate_state.get("bear_count", 0) >= max_individual_rounds
        ):
            if "investment_plan" not in state or not state["investment_plan"]:
                debate_history = debate_state.get("history", "")
                state["investment_plan"] = (
                    f"Research Team Consensus (Individual limit reached):\n{debate_history}"
                )
            print(
                f"⚠️  Warning: Individual researcher exceeded maximum rounds ({max_individual_rounds})"
            )
            return "Trader"

        # Check if we have completed all required rounds
        # Each researcher should speak max_debate_rounds times
        if (
            debate_state["bull_count"] >= self.max_debate_rounds
            and debate_state["bear_count"] >= self.max_debate_rounds
        ):
            # Create investment plan from debate history before going to trader
            if "investment_plan" not in state or not state["investment_plan"]:
                debate_history = debate_state.get("history", "")
                state["investment_plan"] = f"Research Team Consensus:\n{debate_history}"
            return "Trader"

        # Determine who should speak next based on current counts
        # Start with Bull if no one has spoken yet, or if Bear has spoken more than Bull
        if debate_state["bull_count"] == 0 or (
            debate_state["bear_count"] > debate_state["bull_count"]
        ):
            return "Bull Researcher"
        else:
            return "Bear Researcher"
