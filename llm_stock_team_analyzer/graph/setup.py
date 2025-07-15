# LLM Stock Team Analyzer/graph/setup.py

from typing import Dict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode

from llm_stock_team_analyzer.agents.analysts.market_analyst import create_market_analyst
from llm_stock_team_analyzer.agents.analysts.news_analyst import create_news_analyst
from llm_stock_team_analyzer.agents.researchers.bear_researcher import (
    create_bear_researcher,
)
from llm_stock_team_analyzer.agents.researchers.bull_researcher import (
    create_bull_researcher,
)
from llm_stock_team_analyzer.agents.trader.trader import create_trader
from llm_stock_team_analyzer.agents.utils.agent_states import AgentState
from llm_stock_team_analyzer.agents.utils.agent_utils import Toolkit, create_msg_delete

from .conditional_logic import ConditionalLogic


class GraphSetup:
    """Handles the setup and configuration of the agent graph."""

    def __init__(
        self,
        quick_thinking_llm: ChatOpenAI,
        deep_thinking_llm: ChatOpenAI,
        toolkit: Toolkit,
        tool_nodes: Dict[str, ToolNode],
        bull_memory,
        bear_memory,
        trader_memory,
        conditional_logic: ConditionalLogic,
    ):
        """Initialize with required components."""
        self.quick_thinking_llm = quick_thinking_llm
        self.deep_thinking_llm = deep_thinking_llm
        self.toolkit = toolkit
        self.tool_nodes = tool_nodes
        self.bull_memory = bull_memory
        self.bear_memory = bear_memory
        self.trader_memory = trader_memory
        self.conditional_logic = conditional_logic

    def setup_graph(self, selected_analysts=["market", "news"]):
        """Set up and compile the agent workflow graph.

        Args:
            selected_analysts (list): List of analyst types to include. Options are:
                - "market": Market analyst
                - "news": News analyst
        """
        if len(selected_analysts) == 0:
            raise ValueError("Trading Agents Graph Setup Error: no analysts selected!")

        # Validate selected analysts
        valid_analysts = ["market", "news"]
        for analyst in selected_analysts:
            if analyst not in valid_analysts:
                raise ValueError(
                    f"Invalid analyst type: {analyst}. Valid options: {valid_analysts}"
                )

        # Update conditional logic with selected analysts
        self.conditional_logic.selected_analysts = selected_analysts

        # Create analyst nodes
        analyst_nodes = {}
        delete_nodes = {}
        local_tool_nodes = {}  # Renamed to avoid confusion with self.tool_nodes

        if "market" in selected_analysts:
            analyst_nodes["market"] = create_market_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            delete_nodes["market"] = create_msg_delete()
            local_tool_nodes["market"] = self.tool_nodes["market"]

        if "news" in selected_analysts:
            analyst_nodes["news"] = create_news_analyst(
                self.quick_thinking_llm, self.toolkit
            )
            delete_nodes["news"] = create_msg_delete()
            local_tool_nodes["news"] = self.tool_nodes["news"]

        # Create researcher and trader nodes
        bull_researcher_node = create_bull_researcher(
            self.quick_thinking_llm, self.bull_memory
        )
        bear_researcher_node = create_bear_researcher(
            self.quick_thinking_llm, self.bear_memory
        )
        trader_node = create_trader(self.quick_thinking_llm, self.trader_memory)

        # Create workflow
        workflow = StateGraph(AgentState)

        # Add analyst nodes to the graph
        for analyst_type, node in analyst_nodes.items():
            workflow.add_node(f"{analyst_type.capitalize()} Analyst", node)
            workflow.add_node(
                f"Msg Clear {analyst_type.capitalize()}", delete_nodes[analyst_type]
            )
            workflow.add_node(f"tools_{analyst_type}", local_tool_nodes[analyst_type])

        # Add other nodes
        workflow.add_node("Bull Researcher", bull_researcher_node)
        workflow.add_node("Bear Researcher", bear_researcher_node)
        workflow.add_node("Trader", trader_node)

        # Define edges
        # Start with the first analyst
        first_analyst = selected_analysts[0]
        workflow.add_edge(START, f"{first_analyst.capitalize()} Analyst")

        # Connect analysts in sequence (following reference design)
        for i, analyst_type in enumerate(selected_analysts):
            current_analyst = f"{analyst_type.capitalize()} Analyst"
            current_tools = f"tools_{analyst_type}"
            current_clear = f"Msg Clear {analyst_type.capitalize()}"

            # Add conditional edges for current analyst (following reference design)
            conditional_func = getattr(
                self.conditional_logic, f"should_continue_{analyst_type}"
            )
            workflow.add_conditional_edges(
                current_analyst,
                conditional_func,
                [current_tools, current_clear],  # Only two options: tools or clear
            )
            # Tools go back to analyst to process results (like reference code)
            workflow.add_edge(current_tools, current_analyst)

            # Connect to next analyst or to phase checker if this is the last analyst
            if i < len(selected_analysts) - 1:
                next_analyst = f"{selected_analysts[i + 1].capitalize()} Analyst"
                workflow.add_edge(current_clear, next_analyst)
            else:
                # Last analyst connects to analysis phase completion checker
                workflow.add_edge(current_clear, "Analysis Phase Checker")

        # Add analysis phase completion checker node
        def analysis_phase_checker(state: AgentState):
            """Check if analysis phase is complete and announce transition."""
            if self.conditional_logic.are_analysts_complete(state):
                if not state.get("_analysis_complete_announced"):
                    state["_analysis_complete_announced"] = True
                    state["_phase"] = "debate"

            # Return the state with the new flags but preserve all existing data
            return state

        workflow.add_node("Analysis Phase Checker", analysis_phase_checker)
        workflow.add_edge("Analysis Phase Checker", "Bull Researcher")

        # Add remaining edges for the simplified workflow
        workflow.add_conditional_edges(
            "Bull Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bear Researcher": "Bear Researcher",
                "Trader": "Trader",
            },
        )
        workflow.add_conditional_edges(
            "Bear Researcher",
            self.conditional_logic.should_continue_debate,
            {
                "Bull Researcher": "Bull Researcher",
                "Trader": "Trader",
            },
        )
        workflow.add_edge("Trader", END)

        # Compile and return
        return workflow.compile()
