"""
Utility functions for Pydantic AI Agent
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

# Initialize rich console for beautiful output
console = Console()


def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Setup logging configuration

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)

    Returns:
        Configured logger
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def print_welcome_message(agent_name: str, prompt_template: str) -> None:
    """
    Print welcome message with agent information

    Args:
        agent_name: Name of the agent
        prompt_template: Template being used
    """
    welcome_text = f"""
# Welcome to {agent_name}!

**Active Template:** `{prompt_template}`

**Features:**
- 🧠 Long-term memory via Mem0
- 🛡️ Safety guardrails via Guardrails AI
- 📊 Observability via Langfuse
- 🤖 Powered by local Ollama

Type your message and press Enter to chat. Type 'quit' or 'exit' to end the session.
    """
    console.print(Panel(Markdown(welcome_text), title="Pydantic AI Agent", border_style="blue"))


def print_user_message(message: str) -> None:
    """
    Print user message with formatting

    Args:
        message: User message to display
    """
    console.print(f"\n[bold cyan]You:[/bold cyan] {message}")


def print_agent_message(message: str) -> None:
    """
    Print agent response with formatting

    Args:
        message: Agent response to display
    """
    console.print(f"\n[bold green]Agent:[/bold green] {message}\n")


def print_system_message(message: str, style: str = "yellow") -> None:
    """
    Print system message with formatting

    Args:
        message: System message to display
        style: Rich style to apply
    """
    console.print(f"\n[{style}]System: {message}[/{style}]\n")


def print_error(error: str) -> None:
    """
    Print error message with formatting

    Args:
        error: Error message to display
    """
    console.print(f"\n[bold red]Error:[/bold red] {error}\n")


def format_memory_context(memories: list) -> str:
    """
    Format memory context for display

    Args:
        memories: List of memory items

    Returns:
        Formatted memory string
    """
    if not memories:
        return "No previous context found."

    context = "Relevant context from previous conversations:\n"
    for i, memory in enumerate(memories, 1):
        context += f"{i}. {memory}\n"

    return context


def create_conversation_metadata(user_id: str, session_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Create metadata for conversation tracking

    Args:
        user_id: User identifier
        session_id: Optional session identifier

    Returns:
        Metadata dictionary
    """
    return {
        "user_id": user_id,
        "session_id": session_id or f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
        "timestamp": datetime.now().isoformat(),
    }


def sanitize_input(user_input: str) -> str:
    """
    Sanitize user input

    Args:
        user_input: Raw user input

    Returns:
        Sanitized input string
    """
    # Strip whitespace
    sanitized = user_input.strip()

    # Basic sanitization - can be extended
    # For now, just remove any null bytes
    sanitized = sanitized.replace('\x00', '')

    return sanitized


def is_exit_command(user_input: str) -> bool:
    """
    Check if user wants to exit

    Args:
        user_input: User input to check

    Returns:
        True if exit command, False otherwise
    """
    exit_commands = ['quit', 'exit', 'bye', 'goodbye']
    return user_input.lower().strip() in exit_commands
