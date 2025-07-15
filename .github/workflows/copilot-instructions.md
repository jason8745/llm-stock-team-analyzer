````instructions
---
description: 'LLM Stock Team Analyzer - Python coding conventions and AI agent guidelines'
applyTo: '**/*.py'
---

# LLM Stock Team Analyzer - Coding Conventions & Guidelines

## Language & Communication Rules

### Comments and Documentation
- **ALL comments MUST be written in English** - no exceptions
- Use clear, concise English for code comments, docstrings, and inline documentation
- Variable names, function names, and class names should be in English
- Example: `# Calculate technical indicators for trend analysis` ✅
- Example: `# 計算技術指標進行趨勢分析` ❌

### Agent Mode Communication
- When working in **agent mode** (interactive chat/assistance), respond in **Chinese (Traditional)**
- Provide explanations, analysis, and user communication in Chinese
- Technical discussions about code should be in Chinese when in agent mode
- User-facing messages, logs, and interactive prompts should be in Chinese

## Python Development Standards

### Type Hints and Documentation
- Use comprehensive type hints for all functions and methods
- Include detailed docstrings following **PEP 257** conventions
- Use the `typing` module for complex type annotations (e.g., `List[str]`, `Dict[str, Any]`)
- Document parameters, return values, and raise exceptions

### Function Design
- Write clear, descriptive function names that indicate purpose
- Break down complex functions into smaller, focused units
- Each function should have a single, well-defined responsibility
- Include error handling for edge cases and invalid inputs

### Code Style and Formatting
- Follow **PEP 8** style guide strictly
- Use 4 spaces for indentation (no tabs)
- Line length should not exceed 88 characters (Black formatter standard)
- Use meaningful variable names that explain their purpose
- Add blank lines to separate logical code blocks

### Multi-Agent System Specific Guidelines

#### State Management
- Always validate state transitions in LangGraph workflows
- Include comprehensive logging for state changes and agent interactions
- Use type-safe state definitions with Annotated types
- Handle missing or invalid state gracefully

#### Agent Development
- Each agent should have clear, focused responsibilities
- Include memory integration where appropriate for learning capabilities
- Use tool calling patterns consistently across all agents
- Implement proper error handling for external API calls (Yahoo Finance, Google News)

#### LangGraph Integration
- Follow LangGraph best practices for node and edge definitions
- Use conditional logic functions for workflow control
- Implement proper message handling and state propagation
- Include debug logging for workflow execution tracking

### Testing Requirements
- Write comprehensive unit tests for all critical functionality
- Include edge case testing (empty data, invalid inputs, API failures)
- Test agent interactions and state transitions
- Use pytest fixtures for reusable test data
- Aim for high test coverage on core business logic

### Error Handling and Logging
- Use structured logging with appropriate log levels
- Include context information in error messages
- Handle external API failures gracefully with fallbacks
- Log state transitions and agent decision points
- Use the project's logger utility consistently

### Dependencies and External APIs
- Document all external dependencies and their purposes
- Handle API rate limits and timeouts appropriately
- Include fallback mechanisms for critical external services
- Use environment variables for sensitive configuration

## Development Workflow Guidelines

### Git Commit Messages
- When completing significant features or fixes, suggest meaningful commit messages
- Follow conventional commit format: `type(scope): description`
- Examples:
  - `feat(agents): add bull/bear researcher debate mechanism`
  - `fix(dataflow): handle Yahoo Finance API timeout errors`
  - `refactor(graph): optimize state propagation efficiency`
  - `docs(readme): update installation instructions`

### Pull Request Guidelines
- When asked to provide PR suggestions, always use `git` commands to verify changes
- Include **Why** (reasoning/motivation) and **What** (specific changes) in PR descriptions
- List main changes concisely but comprehensively
- Verify all tests pass before suggesting PR creation
- Include any breaking changes or migration notes

### Code Quality Checkpoints
- Recognize good commit points after implementing complete features
- Suggest commits when:
  - A new agent or major component is implemented
  - Bug fixes are completed and tested
  - Refactoring improves code structure significantly
  - Documentation is updated for user-facing changes

## Project-Specific Patterns

### Agent Implementation Pattern
```python
def create_agent_name(llm, memory_or_toolkit):
    """Create an agent node for the LangGraph workflow.
    
    Args:
        llm: The language model instance to use
        memory_or_toolkit: Memory system or toolkit for agent capabilities
        
    Returns:
        Callable agent node function for LangGraph integration
    """
    def agent_node(state):
        # Agent implementation logic here
        pass
    return agent_node
```

### Tool Integration Pattern
```python
@tool
def tool_name(parameter: str) -> str:
    """Tool description for LLM understanding.
    
    Args:
        parameter: Description of the parameter
        
    Returns:
        str: Description of return value
        
    Raises:
        ToolException: When tool execution fails
    """
    # Tool implementation with error handling
    pass
```

### State Handling Pattern
```python
class AgentState(TypedDict):
    """Type-safe state definition for LangGraph workflow."""
    field_name: Annotated[str, "Description of field purpose"]
    # Use Annotated types for clear state documentation
```

## Example of Proper Implementation

```python
from typing import Dict, List, Optional
from langchain_core.tools import tool
from llm_stock_team_analyzer.utils.logger import get_logger

logger = get_logger(__name__)

def analyze_market_trends(
    stock_data: Dict[str, float], 
    indicators: List[str]
) -> Optional[Dict[str, float]]:
    """
    Analyze market trends using technical indicators.
    
    This function processes stock price data and calculates specified
    technical indicators to determine market trend direction and strength.
    
    Args:
        stock_data: Dictionary containing OHLCV stock price data
        indicators: List of technical indicator names to calculate
        
    Returns:
        Dict containing calculated indicator values, or None if analysis fails
        
    Raises:
        ValueError: If stock_data is empty or indicators list is invalid
        CalculationError: If indicator calculation fails
    """
    if not stock_data:
        logger.warning("Empty stock data provided for trend analysis")
        raise ValueError("Stock data cannot be empty")
    
    try:
        # Calculate technical indicators with proper error handling
        results = {}
        for indicator in indicators:
            # Implementation logic here
            pass
            
        logger.info(f"Successfully calculated {len(results)} indicators")
        return results
        
    except Exception as e:
        logger.error(f"Market trend analysis failed: {str(e)}")
        raise CalculationError(f"Failed to analyze trends: {str(e)}")
```

Remember: This is a sophisticated multi-agent financial analysis system. Code quality, reliability, and clear documentation are essential for maintaining and extending the agent capabilities.
````
