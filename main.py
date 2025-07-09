#!/usr/bin/env python3
"""
LLM Stock Team Analyzer - Main CLI Entry Point

A modernized, local-only stock analysis system using AI agents.
"""

import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.text import Text

from llm_stock_team_analyzer.configs.config import get_config
from llm_stock_team_analyzer.graph.trading_graph import TradingAgentsGraph

console = Console()


def display_banner():
    """Display welcome banner."""
    banner = """
[bold blue]🔍 LLM Stock Team Analyzer[/bold blue]
[dim]AI-Powered Multi-Agent Stock Analysis Framework[/dim]

Available Analysis Components:
• [green]Market Analyst[/green] - Technical analysis using Yahoo Finance data
• [green]News Analyst[/green] - Sentiment analysis from Google News  
• [green]Bull Researcher[/green] - Optimistic investment perspective
• [green]Bear Researcher[/green] - Risk-focused investment perspective
• [green]Trader[/green] - Final trading decision synthesis

[dim]All analysis is performed locally using only available data sources.[/dim]
    """
    console.print(Panel(banner, border_style="blue", padding=(1, 2)))


def get_ticker_input() -> str:
    """Get ticker symbol from user."""
    while True:
        ticker = (
            Prompt.ask(
                "[bold cyan]Enter stock ticker symbol[/bold cyan]", default="AAPL"
            )
            .strip()
            .upper()
        )

        if ticker and len(ticker) <= 10:  # Basic validation
            return ticker
        console.print("[red]Please enter a valid ticker symbol (1-10 characters)[/red]")


def get_analysis_date() -> str:
    """Get analysis date from user."""
    default_date = datetime.now().strftime("%Y-%m-%d")

    while True:
        date_input = Prompt.ask(
            "[bold cyan]Enter analysis date[/bold cyan]", default=default_date
        ).strip()

        try:
            # Validate date format
            datetime.strptime(date_input, "%Y-%m-%d")
            return date_input
        except ValueError:
            console.print("[red]Please enter date in YYYY-MM-DD format[/red]")


def display_progress_step(step: str, details: str = ""):
    """Display current analysis step."""
    if details:
        console.print(f"[bold yellow]► {step}[/bold yellow]: {details}")
    else:
        console.print(f"[bold yellow]► {step}[/bold yellow]")


def display_agent_output(agent_name: str, content: str):
    """Display output from a specific agent."""
    console.print()
    console.print(
        Panel(
            Markdown(content),
            title=f"[bold green]{agent_name}[/bold green]",
            border_style="green",
            padding=(1, 2),
        )
    )


def display_debate_step(step_num: int, total_steps: int, description: str):
    """Display debate/discussion step."""
    console.print(
        f"\n[bold magenta] Debate Round {step_num}/{total_steps}:[/bold magenta] {description}"
    )
    console.print(
        "[dim]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/dim]"
    )


def run_analysis(ticker: str, analysis_date: str) -> Dict[str, Any]:
    """Run the complete stock analysis workflow."""

    # Initialize configuration and graph
    display_progress_step("Initializing AI agents")

    config = get_config()
    # Use both available analysts
    selected_analysts = ["market", "news"]

    try:
        graph = TradingAgentsGraph(
            selected_analysts=selected_analysts, config=config, debug=True
        )
    except Exception as e:
        console.print(f"[red]Error initializing analysis system: {e}[/red]")
        return {}

    # Create initial state
    display_progress_step(
        "Setting up analysis parameters", f"Ticker: {ticker}, Date: {analysis_date}"
    )

    try:
        initial_state = graph.propagator.create_initial_state(ticker, analysis_date)
        graph_args = graph.propagator.get_graph_args()
    except Exception as e:
        console.print(f"[red]Error setting up analysis: {e}[/red]")
        return {}

    # Run analysis with progress display and retry logic
    console.print()
    console.print("[bold blue]🚀 Starting Multi-Agent Analysis Workflow[/bold blue]")
    console.print()

    final_state = {}
    current_agent = None
    debate_started = False
    analysis_phase_complete = False
    max_retries = 3
    retry_count = 0

    while retry_count < max_retries:
        try:
            with console.status("[bold green]Analyzing...", spinner="dots") as status:
                for chunk in graph.graph.stream(initial_state, **graph_args):
                    # Always update final_state with each chunk to accumulate results
                    final_state.update(chunk)

                    # Check if analysis phase is complete (controlled by graph)
                    if not analysis_phase_complete and chunk.get(
                        "_analysis_complete_announced"
                    ):
                        analysis_phase_complete = True
                        status.stop()
                        console.print()
                        console.print(
                            "[bold green]✅ All Analysis Complete![/bold green]"
                        )
                        console.print()

                        # Update final state with all analysis results
                        final_state.update(chunk)

                        # Force display all available analysis results from final_state
                        # Try to find and display market analysis
                        market_content = None
                        for key in [
                            "market_report",
                            "market_analysis",
                            "technical_analysis",
                        ]:
                            if key in final_state and final_state[key]:
                                market_content = final_state[key]
                                break

                        if market_content:
                            display_progress_step(
                                "Market Analyst", "Technical analysis complete"
                            )
                            display_agent_output("📈 Market Analyst", market_content)
                        else:
                            console.print(
                                "[yellow]Warning: No market analysis found[/yellow]"
                            )

                        # Try to find and display news analysis
                        news_content = None
                        for key in [
                            "news_report",
                            "news_analysis",
                            "sentiment_analysis",
                        ]:
                            if key in final_state and final_state[key]:
                                news_content = final_state[key]
                                break

                        if news_content:
                            display_progress_step(
                                "News Analyst", "News analysis complete"
                            )
                            display_agent_output("📰 News Analyst", news_content)
                        else:
                            console.print(
                                "[yellow]Warning: No news analysis found[/yellow]"
                            )

                        # Proceed to debate if we have any analysis results
                        if market_content or news_content:
                            console.print()
                            console.print(
                                "[bold cyan]🎭 Starting Research Debate...[/bold cyan]"
                            )
                            console.print()
                            status.start()
                        else:
                            console.print(
                                "[yellow]Warning: No analysis results available to start debate[/yellow]"
                            )
                            # Still try to continue in case results are in different keys
                            console.print()
                            console.print(
                                "[bold cyan]🎭 Attempting to Start Research Debate...[/bold cyan]"
                            )
                            console.print()
                            status.start()

                    # Only show progress during analysis phase
                    if not analysis_phase_complete:
                        # Just show tool activity without detailed output during analysis
                        continue

                    # After analysis is complete, show all content including debate
                    # Check for debate state changes
                    if (
                        "investment_debate_state" in chunk
                        and chunk["investment_debate_state"]
                    ):
                        debate_state = chunk["investment_debate_state"]
                        if (
                            "current_response" in debate_state
                            and debate_state["current_response"]
                        ):
                            current_response = debate_state["current_response"]

                            # Bull Researcher output
                            if current_response.startswith("Bull Analyst:"):
                                status.stop()
                                if not debate_started:
                                    console.print()
                                    console.print(
                                        "[bold cyan]🎭 Starting Bull vs Bear Research Debate[/bold cyan]"
                                    )
                                    console.print()
                                    debate_started = True
                                if current_agent != "Bull Researcher":
                                    # Use the actual count from debate state
                                    bull_count = debate_state.get("bull_count", 0)
                                    max_rounds = config.get("max_debate_rounds", 1)
                                    current_agent = "Bull Researcher"
                                    display_debate_step(
                                        bull_count,
                                        max_rounds,
                                        "Bull researcher presenting optimistic analysis",
                                    )
                                display_agent_output(
                                    "🐂 Bull Researcher", current_response
                                )
                                status.start()
                                continue  # Skip other checks for this chunk

                            # Bear Researcher output
                            elif current_response.startswith("Bear Analyst:"):
                                status.stop()
                                if not debate_started:
                                    console.print()
                                    console.print(
                                        "[bold cyan]🎭 Starting Bull vs Bear Research Debate[/bold cyan]"
                                    )
                                    console.print()
                                    debate_started = True
                                if current_agent != "Bear Researcher":
                                    # Use the actual count from debate state
                                    bear_count = debate_state.get("bear_count", 0)
                                    max_rounds = config.get("max_debate_rounds", 1)
                                    current_agent = "Bear Researcher"
                                    display_debate_step(
                                        bear_count,
                                        max_rounds,
                                        "Bear researcher presenting risk analysis",
                                    )
                                display_agent_output(
                                    "🐻 Bear Researcher", current_response
                                )
                                status.start()
                                continue  # Skip other checks for this chunk

                    # Investment plan (from research consensus)
                    elif (
                        "investment_plan" in chunk
                        and chunk["investment_plan"]
                        and current_agent != "Research Consensus"
                    ):
                        current_agent = "Research Consensus"
                        status.stop()
                        if debate_started:
                            console.print()
                            console.print(
                                "[bold cyan]🤝 Debate Complete - Synthesizing Consensus[/bold cyan]"
                            )
                            console.print()
                        display_progress_step(
                            "Research Team", "Synthesizing bull and bear perspectives"
                        )
                        display_agent_output(
                            "Research Team Consensus", chunk["investment_plan"]
                        )
                        status.start()

                    # Trader final decision
                    elif (
                        "trader_investment_plan" in chunk
                        and chunk["trader_investment_plan"]
                        and current_agent != "Trader"
                    ):
                        current_agent = "Trader"
                        status.stop()
                        display_progress_step(
                            "Trader", "Synthesizing final trading recommendations"
                        )
                        display_agent_output(
                            "💰 Trading Decision", chunk["trader_investment_plan"]
                        )
                        status.start()

                    # Final trade decision (alternative field name)
                    elif (
                        "final_trade_decision" in chunk
                        and chunk["final_trade_decision"]
                        and current_agent != "Final Trader"
                    ):
                        current_agent = "Final Trader"
                        status.stop()
                        display_progress_step("Trader", "Final trading decision")
                        display_agent_output(
                            "💰 Final Trading Decision", chunk["final_trade_decision"]
                        )
                        status.start()

                    # Note: final_state is already updated at the beginning of the loop

            # If we get here, analysis completed successfully
            break

        except KeyboardInterrupt:
            console.print("\n[yellow]Analysis interrupted by user[/yellow]")
            return final_state

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "rate limit" in error_msg.lower():
                retry_count += 1
                if retry_count < max_retries:
                    wait_time = 60 * retry_count  # Exponential backoff: 60s, 120s, 180s
                    console.print(
                        f"\n[yellow]⚠️  Rate limit hit. Waiting {wait_time} seconds before retry ({retry_count}/{max_retries})...[/yellow]"
                    )

                    # Show countdown
                    for remaining in range(wait_time, 0, -1):
                        console.print(
                            f"\r[dim]Retrying in {remaining} seconds...[/dim]", end=""
                        )
                        time.sleep(1)
                    console.print("\n[green]Retrying analysis...[/green]")
                else:
                    console.print(
                        f"\n[red]Rate limit exceeded after {max_retries} retries. Please try again later.[/red]"
                    )
                    return final_state
            else:
                console.print(f"\n[red]Error during analysis: {e}[/red]")
                return final_state

    console.print()
    console.print("[bold green]✅ Analysis Complete![/bold green]")

    return final_state


def display_final_summary(results: Dict[str, Any], ticker: str):
    """Display final analysis summary."""
    if not results:
        console.print("[red]No analysis results to display[/red]")
        return

    console.print()
    console.print(
        Panel(
            f"[bold blue]Final Analysis Summary for {ticker}[/bold blue]",
            border_style="blue",
        )
    )

    # Display key results with all possible field variations
    sections = [
        (["market_report"], "📈 Market Analysis"),
        (["news_report"], "📰 News Analysis"),
        (
            ["debate_result", "investment_plan", "debate_summary"],
            "🎯 Research Team Decision",
        ),
        (
            ["trader_investment_plan", "final_trade_decision"],
            "💰 Trading Recommendation",
        ),
    ]

    for keys, title in sections:
        # Get the first non-empty result from alternative field names
        content = next((results[k] for k in keys if k in results and results[k]), None)
        if content:
            console.print()
            console.print(
                Panel(
                    Markdown(content), title=title, border_style="cyan", padding=(1, 2)
                )
            )

    # Log any missing components
    missing = []
    if not any(k in results and results[k] for k in ["market_report"]):
        missing.append("Market Analysis")
    if not any(k in results and results[k] for k in ["news_report"]):
        missing.append("News Analysis")
    if not any(
        k in results and results[k]
        for k in ["debate_result", "investment_plan", "debate_summary"]
    ):
        missing.append("Research Team Decision")
    if not any(
        k in results and results[k]
        for k in ["trader_investment_plan", "final_trade_decision"]
    ):
        missing.append("Trading Decision")

    if missing:
        console.print(
            "\n[yellow]Note: The following components were not completed:[/yellow]"
        )
        for m in missing:
            console.print(f"[yellow]- {m}[/yellow]")


def main():
    """Main CLI entry point."""
    try:
        # Display welcome banner
        display_banner()

        # Get user inputs
        ticker = get_ticker_input()
        analysis_date = get_analysis_date()

        console.print()
        console.print(
            f"[bold green]Starting analysis for {ticker} on {analysis_date}[/bold green]"
        )

        # Run analysis
        results = run_analysis(ticker, analysis_date)

        # Display results
        display_final_summary(results, ticker)

        console.print()
        console.print(
            "[dim]Analysis completed. Thank you for using LLM Stock Team Analyzer![/dim]"
        )

    except KeyboardInterrupt:
        console.print("\n[yellow]Goodbye![/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
