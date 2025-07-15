# LLM Stock Team Analyzer/graph/trading_graph.py

import json
import os
from pathlib import Path
from typing import Any, Dict

from langchain_openai import AzureChatOpenAI
from langgraph.prebuilt import ToolNode

from llm_stock_team_analyzer.agents import *
from llm_stock_team_analyzer.agents.utils.memory import FinancialSituationMemory
from llm_stock_team_analyzer.configs.config import get_config, get_pydantic_config
from llm_stock_team_analyzer.utils.logger import get_logger

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

        # Set up logger
        self.logger = get_logger(__name__)

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
                    self.toolkit.get_company_info,
                    self.toolkit.get_google_news,
                ]
            ),
        }

    def propagate(self, company_name, trade_date):
        """Run the trading agents graph for a company on a specific date."""

        self.ticker = company_name
        self.logger.info(
            f"🚀 Starting trading graph propagation for {company_name} on {trade_date}"
        )

        # Initialize state
        init_agent_state = self.propagator.create_initial_state(
            company_name, trade_date
        )
        args = self.propagator.get_graph_args()

        self.logger.info(
            f"📊 Initial state created with analysts: {self.selected_analysts}"
        )
        self.logger.debug(f"Initial state keys: {list(init_agent_state.keys())}")

        if self.debug:
            # Debug mode with tracing
            trace = []
            step_count = 0
            for chunk in self.graph.stream(init_agent_state, **args):
                step_count += 1
                node_name = list(chunk.keys())[0] if chunk else "Unknown"

                self.logger.info(f"🔄 Step {step_count}: Executing node '{node_name}'")

                # Log state transitions for debate phase
                if node_name in ["Bull Researcher", "Bear Researcher"]:
                    self._log_debate_state_transition(chunk, node_name, step_count)
                elif "Analyst" in node_name:
                    self._log_analyst_state(chunk, node_name)
                elif node_name == "Analysis Phase Checker":
                    self._log_phase_transition(chunk)
                elif node_name == "Trader":
                    self._log_trader_state(chunk)

                if len(chunk.get("messages", [])) > 0:
                    chunk["messages"][-1].pretty_print()

                trace.append(chunk)

            final_state = trace[-1] if trace else init_agent_state
            self.logger.info(f"✅ Graph execution completed in {step_count} steps")
        else:
            # Standard mode without tracing
            self.logger.info("🔄 Running graph in standard mode (no tracing)")
            final_state = self.graph.invoke(init_agent_state, **args)
            self.logger.info("✅ Graph execution completed")

        # Store current state for reflection
        self.curr_state = final_state

        # Log final state summary
        self._log_final_state_summary(final_state)

        # Log state
        self._log_state(trade_date, final_state)

        # Return decision and processed signal (handle case where trader hasn't run)
        trade_decision = final_state.get("final_trade_decision", "")
        signal = self.process_signal(trade_decision) if trade_decision else "NO_SIGNAL"

        self.logger.info(
            f"🎯 Final trade decision: {trade_decision[:100]}..."
            if len(trade_decision) > 100
            else f"🎯 Final trade decision: {trade_decision}"
        )
        self.logger.info(f"📶 Processed signal: {signal}")

        return final_state, signal

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

    def _log_debate_state_transition(self, chunk, node_name, step_count):
        """Log detailed information about debate state transitions."""
        state = chunk.get(list(chunk.keys())[0], {})
        debate_state = state.get("investment_debate_state", {})

        self.logger.info(f"🗣️  {node_name} - Step {step_count}")
        self.logger.info(
            f"   📊 Debate counts - Bull: {debate_state.get('bull_count', 0)}, Bear: {debate_state.get('bear_count', 0)}, Total: {debate_state.get('count', 0)}"
        )

        current_response = debate_state.get("current_response", "")
        if current_response:
            self.logger.info(f"   💬 Current response: {current_response[:150]}...")

        history = debate_state.get("history", "")
        if history:
            self.logger.debug(f"   📚 History length: {len(history)} characters")

    def _log_analyst_state(self, chunk, node_name):
        """Log analyst execution state."""
        state = chunk.get(list(chunk.keys())[0], {})

        self.logger.info(f"📈 {node_name} execution")
        if "market" in node_name.lower() and state.get("market_report"):
            self.logger.info(
                f"   ✅ Market report generated ({len(state['market_report'])} chars)"
            )
        elif "news" in node_name.lower() and state.get("news_report"):
            self.logger.info(
                f"   ✅ News report generated ({len(state['news_report'])} chars)"
            )

    def _log_phase_transition(self, chunk):
        """Log phase transition information."""
        state = chunk.get(list(chunk.keys())[0], {})

        self.logger.info("🔄 Analysis Phase Checker")

        # Check which reports are available
        available_reports = []
        if state.get("market_report"):
            available_reports.append("market")
        if state.get("news_report"):
            available_reports.append("news")

        self.logger.info(f"   📋 Available reports: {available_reports}")
        self.logger.info(f"   🎯 Required analysts: {self.selected_analysts}")

        if state.get("_analysis_complete_announced"):
            self.logger.info(
                "   ✅ Analysis phase marked as complete - transitioning to debate"
            )
        else:
            self.logger.warning("   ⚠️  Analysis phase not yet complete")

    def _log_trader_state(self, chunk):
        """Log trader execution state."""
        state = chunk.get(list(chunk.keys())[0], {})

        self.logger.info("💼 Trader execution")

        # Check if investment plan is available
        investment_plan = state.get("investment_plan", "")
        if investment_plan:
            self.logger.info(
                f"   📋 Investment plan available ({len(investment_plan)} chars)"
            )
        else:
            self.logger.warning("   ⚠️  No investment plan available for trader")

        # Check debate state
        debate_state = state.get("investment_debate_state", {})
        if debate_state:
            self.logger.info(
                f"   🗣️  Debate state - Bull: {debate_state.get('bull_count', 0)}, Bear: {debate_state.get('bear_count', 0)}"
            )

    def _log_final_state_summary(self, final_state):
        """Log a summary of the final state."""
        self.logger.info("📋 Final State Summary:")

        # Check analysts reports
        if final_state.get("market_report"):
            self.logger.info("   ✅ Market report: Available")
        else:
            self.logger.warning("   ❌ Market report: Missing")

        if final_state.get("news_report"):
            self.logger.info("   ✅ News report: Available")
        else:
            self.logger.warning("   ❌ News report: Missing")

        # Check debate state
        debate_state = final_state.get("investment_debate_state", {})
        if debate_state:
            bull_count = debate_state.get("bull_count", 0)
            bear_count = debate_state.get("bear_count", 0)
            total_count = debate_state.get("count", 0)

            self.logger.info(
                f"   🗣️  Debate rounds - Bull: {bull_count}, Bear: {bear_count}, Total: {total_count}"
            )

            if bull_count > 0 or bear_count > 0:
                self.logger.info("   ✅ Debate phase: Executed")
            else:
                self.logger.warning("   ⚠️  Debate phase: No rounds executed")

            # Check debate content
            history = debate_state.get("history", "")
            if history:
                self.logger.info(f"   📚 Debate history: {len(history)} characters")
            else:
                self.logger.warning("   📚 Debate history: Empty")
        else:
            self.logger.warning("   ❌ Debate state: Missing")

        # Check trader outputs
        if final_state.get("trader_investment_plan"):
            self.logger.info("   ✅ Trader investment plan: Available")
        else:
            self.logger.warning("   ❌ Trader investment plan: Missing")

        if final_state.get("final_trade_decision"):
            self.logger.info("   ✅ Final trade decision: Available")
        else:
            self.logger.warning("   ❌ Final trade decision: Missing")
