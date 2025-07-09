# LLM Stock Team Analyzer/graph/trading_graph.py

import json
import os
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import ToolNode

from llm_stock_team_analyzer.agents import *
from llm_stock_team_analyzer.agents.utils.agent_states import (
    AgentState,
    InvestDebateState,
)
from llm_stock_team_analyzer.agents.utils.memory import FinancialSituationMemory
from llm_stock_team_analyzer.configs.config import get_config, get_pydantic_config

from .conditional_logic import ConditionalLogic
from .propagation import Propagator
from .reflection import Reflector
from .setup import GraphSetup
from .signal_processing import SignalProcessor


class TradingAgentsGraph:
    """Main class that orchestrates the trading agents framework."""

    def __init__(
        self,
        selected_analysts=["market", "news"],
        debug=False,
        config: Dict[str, Any] = None,
    ):
        """Initialize the trading agents graph and components.

        Args:
            selected_analysts: List of analyst types to include
            debug: Whether to run in debug mode
            config: Configuration dictionary. If None, uses default config
        """
        self.debug = debug
        self.selected_analysts = selected_analysts

        # Load configuration
        if config:
            self.config = config
            self.pydantic_config = None  # If dict config provided, don't use pydantic
        else:
            self.config = get_config()
            self.pydantic_config = get_pydantic_config()

        # Create necessary directories
        if "project_dir" in self.config:
            os.makedirs(
                os.path.join(self.config["project_dir"], "dataflows/data_cache"),
                exist_ok=True,
            )

        # Initialize LLMs using Azure OpenAI with pydantic config
        if self.pydantic_config:
            # Use pydantic config for proper Azure OpenAI setup
            self.deep_thinking_llm = AzureChatOpenAI(
                azure_deployment=self.pydantic_config.azure_openai.deployment,
                azure_endpoint=self.pydantic_config.azure_openai.endpoint,
                api_version=self.pydantic_config.azure_openai.api_version,
                api_key=self.pydantic_config.azure_openai.subscription_key.get_secret_value(),
                temperature=self.pydantic_config.llm.temperature,
                max_tokens=self.pydantic_config.llm.max_tokens,
            )

            # Use the same model for both deep and quick thinking
            self.quick_thinking_llm = AzureChatOpenAI(
                azure_deployment=self.pydantic_config.azure_openai.deployment,
                azure_endpoint=self.pydantic_config.azure_openai.endpoint,
                api_version=self.pydantic_config.azure_openai.api_version,
                api_key=self.pydantic_config.azure_openai.subscription_key.get_secret_value(),
                temperature=self.pydantic_config.llm.temperature,
                max_tokens=self.pydantic_config.llm.max_tokens,
            )
        else:
            # Fallback to dict config (for compatibility)
            self.deep_thinking_llm = AzureChatOpenAI(
                azure_deployment=self.config.get("azure_deployment", "gpt-4"),
                azure_endpoint=self.config.get("azure_endpoint"),
                api_version=self.config.get("azure_api_version", "2024-02-15-preview"),
                api_key=self.config.get("azure_subscription_key"),
                temperature=self.config.get("temperature", 0.5),
                max_tokens=self.config.get("max_tokens", 4096),
            )

            self.quick_thinking_llm = AzureChatOpenAI(
                azure_deployment=self.config.get("azure_deployment", "gpt-4"),
                azure_endpoint=self.config.get("azure_endpoint"),
                api_version=self.config.get("azure_api_version", "2024-02-15-preview"),
                api_key=self.config.get("azure_subscription_key"),
                temperature=self.config.get("temperature", 0.5),
                max_tokens=self.config.get("max_tokens", 4096),
            )

        self.toolkit = Toolkit(config=self.config)

        # Initialize memories
        self.bull_memory = FinancialSituationMemory("bull_memory", self.config)
        self.bear_memory = FinancialSituationMemory("bear_memory", self.config)
        self.trader_memory = FinancialSituationMemory("trader_memory", self.config)

        # Create tool nodes
        self.tool_nodes = self._create_tool_nodes()

        # Initialize components
        self.conditional_logic = ConditionalLogic(
            max_debate_rounds=self.config.get("max_debate_rounds", 1),
            selected_analysts=self.selected_analysts,
        )
        self.graph_setup = GraphSetup(
            self.quick_thinking_llm,
            self.deep_thinking_llm,
            self.toolkit,
            self.tool_nodes,
            self.bull_memory,
            self.bear_memory,
            self.trader_memory,
            self.conditional_logic,
        )

        self.propagator = Propagator()
        self.reflector = Reflector(self.quick_thinking_llm)
        self.signal_processor = SignalProcessor(self.quick_thinking_llm)

        # State tracking
        self.curr_state = None
        self.ticker = None
        self.log_states_dict = {}  # date to full state dict

        # Set up the graph
        self.graph = self.graph_setup.setup_graph(selected_analysts)

    def _create_tool_nodes(self) -> Dict[str, ToolNode]:
        """Create tool nodes for different data sources."""
        return {
            "market": ToolNode(
                [
                    self.toolkit.get_YFin_data,
                    self.toolkit.get_stockstats_indicators_report,
                ]
            ),
            "news": ToolNode(
                [
                    self.toolkit.get_google_news,
                ]
            ),
        }

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        self.ticker = company_name

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        args = self.propagator.get_graph_args()

        if self.debug:
            # Debug mode with tracing
            trace = []
            for chunk in self.graph.stream(init_agent_state, **args):
                if len(chunk["messages"]) == 0:
                    pass
                else:
                    chunk["messages"][-1].pretty_print()
                    trace.append(chunk)

            final_state = trace[-1]
        else:
            # Standard mode without tracing
            final_state = self.graph.invoke(init_agent_state, **args)

        # Store current state for reflection
        self.curr_state = final_state

        # Log state
        self._log_state(trade_date, final_state)

        # Return decision and processed signal (handle case where trader hasn't run)
        trade_decision = final_state.get("final_trade_decision", "")
        return final_state, self.process_signal(
            trade_decision
        ) if trade_decision else "NO_SIGNAL"

    def _log_state(self, trade_date, final_state):
        """Log the final state to a JSON file."""
        # Safely access investment_debate_state with defaults
        debate_state = final_state.get("investment_debate_state", {})

        self.log_states_dict[str(trade_date)] = {
            "company_of_interest": final_state["company_of_interest"],
            "trade_date": final_state["trade_date"],
            "market_report": final_state["market_report"],
            "news_report": final_state["news_report"],
            "investment_debate_state": {
                "bull_history": debate_state.get("bull_history", ""),
                "bear_history": debate_state.get("bear_history", ""),
                "history": debate_state.get("history", ""),
                "current_response": debate_state.get("current_response", ""),
                "judge_decision": debate_state.get("judge_decision", ""),
            },
            "trader_investment_decision": final_state.get("trader_investment_plan", ""),
            "investment_plan": final_state.get("investment_plan", ""),
            "final_trade_decision": final_state.get("final_trade_decision", ""),
        }

        # Save to file
        directory = Path(f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/")
        directory.mkdir(parents=True, exist_ok=True)

        with open(
            f"eval_results/{self.ticker}/TradingAgentsStrategy_logs/full_states_log_{trade_date}.json",
            "w",
        ) as f:
            json.dump(self.log_states_dict, f, indent=4)

    def reflect_and_remember(self, returns_losses):
        """Reflect on decisions and update memory based on returns."""
        self.reflector.reflect_bull_researcher(
            self.curr_state, returns_losses, self.bull_memory
        )
        self.reflector.reflect_bear_researcher(
            self.curr_state, returns_losses, self.bear_memory
        )
        self.reflector.reflect_trader(
            self.curr_state, returns_losses, self.trader_memory
        )

    def process_signal(self, full_signal):
        """Process a signal to extract the core decision."""
        return self.signal_processor.process_signal(full_signal)
