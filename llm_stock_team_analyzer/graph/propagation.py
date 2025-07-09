# LLM Stock Team Analyzer/graph/propagation.py

from typing import Any, Dict

from llm_stock_team_analyzer.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
)


class Propagator:
    """Handles state initialization and propagation through the graph."""

    def __init__(self, max_recur_limit=100):
        """Initialize with configuration parameters."""
        self.max_recur_limit = max_recur_limit

    def create_initial_state(
        self, company_name: str, trade_date: str
    ) -> Dict[str, Any]:
        """Create the initial state for the agent graph."""
        return {
            "messages": [("human", company_name)],
            "company_of_interest": company_name,
            "trade_date": str(trade_date),
            "investment_debate_state": InvestDebateState(
                {
                    "history": "",
                    "current_response": "",
                    "count": 0,
                    "bull_history": "",
                    "bear_history": "",
                    "judge_decision": "",
                }
            ),
            "market_report": "",
            "news_report": "",
            "investment_plan": "",
        }

    def get_graph_args(self) -> Dict[str, Any]:
        """Get arguments for the graph invocation."""
        return {
            "stream_mode": "values",
            "config": {"recursion_limit": self.max_recur_limit},
        }
