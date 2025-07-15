# LLM Stock Team Analyzer/graph/conditional_logic.py

from llm_stock_team_analyzer.agents.utils.agent_states import AgentState
from llm_stock_team_analyzer.utils.logger import get_logger


class ConditionalLogic:
    """Handles conditional logic for determining graph flow."""

    def __init__(self, max_debate_rounds=1, selected_analysts=None):
        """Initialize with configuration parameters."""
        self.max_debate_rounds = max_debate_rounds
        self.selected_analysts = selected_analysts or ["market", "news"]
        self.logger = get_logger(__name__)

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
        is_complete = completed_analysts == required_analysts

        self.logger.info("🔍 Checking analyst completion:")
        self.logger.info(f"   Required: {required_analysts}")
        self.logger.info(f"   Completed: {completed_analysts}")
        self.logger.info(f"   Is complete: {is_complete}")

        return is_complete

    def check_analysis_phase_complete(self, state: AgentState) -> str:
        """Check if analysis phase is complete and should transition to debate."""
        if not hasattr(state, "_analysis_complete_announced"):
            if self.are_analysts_complete(state):
                # Mark that analysis is complete to prevent repeated announcements
                state["_analysis_complete_announced"] = True
                state["_phase"] = "debate"
                self.logger.info(
                    "✅ Analysis phase complete - transitioning to debate phase"
                )
                return "analysis_complete"

        self.logger.info("🔄 Analysis phase continuing...")
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
            self.logger.info("🆕 Initialized debate state")

        debate_state = state["investment_debate_state"]
        bull_count = debate_state.get("bull_count", 0)
        bear_count = debate_state.get("bear_count", 0)
        total_count = debate_state.get("count", 0)
        history = debate_state.get("history", "")

        self.logger.info(
            f"🗣️  Debate 狀態：Bull({bull_count}) Bear({bear_count}) 總計({total_count}/{self.max_debate_rounds * 2}) History({len(history)}字符)"
        )

        # Enhanced safety checks to prevent infinite loops
        max_total_rounds = self.max_debate_rounds * 4  # Safety buffer
        max_individual_rounds = (
            self.max_debate_rounds * 2
        )  # Extra safety per researcher

        # Force end if too many total rounds
        if debate_state.get("count", 0) >= max_total_rounds:
            self.logger.warning(
                f"⚠️  Warning: Debate exceeded maximum total rounds ({max_total_rounds}) - forcing to Trader"
            )
            return "Trader"

        # Force end if any researcher exceeded individual limit
        if (
            debate_state.get("bull_count", 0) >= max_individual_rounds
            or debate_state.get("bear_count", 0) >= max_individual_rounds
        ):
            self.logger.warning(
                f"⚠️  Warning: Individual researcher exceeded maximum rounds ({max_individual_rounds}) - forcing to Trader"
            )
            return "Trader"

        # Check if we have completed all required rounds
        # Each researcher should speak max_debate_rounds times
        if (
            debate_state["bull_count"] >= self.max_debate_rounds
            and debate_state["bear_count"] >= self.max_debate_rounds
        ):
            self.logger.info(
                "✅ Debate completed all required rounds - proceeding to Trader"
            )
            return "Trader"

        # Determine who should speak next based on current counts
        # Logic: Bull speaks first, then alternate. When counts are equal, Bull speaks next.
        next_speaker = None
        if debate_state["bull_count"] <= debate_state["bear_count"]:
            next_speaker = "Bull Researcher"
        else:
            next_speaker = "Bear Researcher"

        self.logger.info(f"🎯 下一位發言者：{next_speaker}")
        return next_speaker
