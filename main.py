#!/usr/bin/env python3

from typing import Any

import os
import sys
import json

import duckdb
from openai import OpenAI

from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown
from rich.syntax import Syntax

import config


# Init rich console
console = Console()

# Define Tools (LLM Function Calls)
TOOLS: list[dict[str, Any]] = [
    {
        'type': 'function',
        'function': {
            'name': 'query_database',
            'description': 'Execute a SQL query on the pirate database',
            'parameters': {
                'type': 'object',
                'properties': {
                    'sql': {'type': 'string', 'description': 'SQL query to execute'}
                },
                'required': ['sql']
            }
        }
    }
]


def setup_database() -> duckdb.DuckDBPyConnection:
    """Create and load the DuckDB database from CSV files."""
    # Delete existing database to ensure latest CSV data
    if config.DB_FILE_PATH.is_file():
        os.remove(str(config.DB_FILE_PATH))
    
    # Create database and load CSV data
    conn = duckdb.connect(str(config.DB_FILE_PATH))
    conn.execute(f"CREATE TABLE sailors AS SELECT * FROM read_csv_auto('{config.SAILORS_DATASET_PATH}')")
    conn.execute(f"CREATE TABLE items AS SELECT * FROM read_csv_auto('{config.ITEMS_DATASET_PATH}')")
    conn.close()
    
    # Reopen in read-only mode
    conn = duckdb.connect(str(config.DB_FILE_PATH), read_only=True)
    return conn


def setup_llm_client() -> OpenAI:
    """Validate configuration and create OpenAI client."""
    if not config.LLM_API_KEY:
        console.print(f"[bold red]Error:[/bold red] Missing 'LLM_API_KEY' in .env file.")
        sys.exit(1)
    
    client = OpenAI(
        base_url=config.LLM_API_ENDPOINT,
        api_key=config.LLM_API_KEY
    )
    return client


def load_system_prompt() -> dict[str, str]:
    """Load system prompt from file and return as message dict."""
    if not config.SYSTEM_PROMPT_PATH.is_file():
        console.print(f"[bold red]Error:[/bold red] System prompt missing at {config.SYSTEM_PROMPT_PATH.absolute()}")
        sys.exit(1)
    
    with open(config.SYSTEM_PROMPT_PATH, 'r') as f:
        system_prompt: str = f.read()
    
    return {
        'role': 'system',
        'content': system_prompt,
    }


def execute_tool_calls(conn: duckdb.DuckDBPyConnection, tool_calls: list) -> list[dict[str, Any]]:
    """Execute tool calls and return tool result messages."""
    tool_messages: list[dict[str, Any]] = []
    
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)
        sql = function_args['sql']
        
        # Execute SQL query
        try:
            result = conn.execute(sql).fetchall()
            result_str = json.dumps(result, indent=2, default=str)
        except Exception as e:
            result_str = f"Error executing query: {str(e)}"
        
        # Display execution
        display_tool_execution(function_name, sql, result_str)
        
        # Create tool result message
        tool_message: dict[str, Any] = {
            'role': 'tool',
            'tool_call_id': tool_call.id,
            'content': result_str,
        }
        tool_messages.append(tool_message)
    
    return tool_messages


def display_tool_execution(function_name: str, sql: str, result: str) -> None:
    """Display tool call and its result."""
    console.print(Panel(
        Syntax(sql, 'sql', theme='monokai', line_numbers=False),
        title=f"[bold yellow]Tool Call:[/bold yellow] {function_name}",
        border_style="yellow",
        expand=True
    ))
    
    console.print(Panel(
        Text(result, style="white"),
        title="[bold yellow]Query Result[/bold yellow]",
        border_style="yellow",
        expand=True
    ))
    console.print("")


def get_llm_response(client: OpenAI, messages: list[dict], tools: list[dict]) -> Any:
    """Get response from LLM with status indicator."""
    with console.status("[bold blue]Thinking...[/bold blue]", spinner="dots"):
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=messages,
            tools=tools,
        )
    return response.choices[0].message


def display_assistant_response(response_obj: Any) -> None:
    """Display assistant's reasoning and final response."""
    response_reasoning: str | None = getattr(response_obj, 'reasoning_content', None)
    response_content: str = response_obj.content
    
    if response_reasoning:
        console.print(Panel(
            Text(response_reasoning, style="dim italic white"),
            title="[dim]Reasoning Process[/dim]",
            border_style="grey30",
            expand=True
        ))
    
    console.print(Panel(
        Markdown(response_content),
        title="[bold blue]Assistant[/bold blue]",
        border_style="blue",
        expand=True
    ))
    console.print("")


def run_chat_loop(conn: duckdb.DuckDBPyConnection, client: OpenAI, system_prompt_message: dict[str, str]) -> None:
    """Run the main chat interaction loop."""
    console.print(5 * '\n', end='')
    console.print("[bold green]Chat Session Started[/bold green]")
    console.print("(Type 'quit' or 'exit' to stop)\n")
    
    messages: list[dict[str, str]] = [system_prompt_message]
    
    while True:
        console.rule("[bold green]User[/bold green]", style="green")
        
        # Get user input
        try:
            user_input = input("\n> ")
        except KeyboardInterrupt:
            break
        
        if user_input.lower() in ['quit', 'exit']:
            break
        
        user_message: dict[str, str] = {
            'role': 'user',
            'content': user_input,
        }
        messages.append(user_message)
        
        # Get initial LLM response
        response_obj = get_llm_response(client, messages, TOOLS)
        
        # Handle tool calls (may need multiple rounds)
        while response_obj.tool_calls:
            # Add assistant message with tool calls to history
            messages.append(response_obj)
            
            # Execute all tool calls
            tool_messages = execute_tool_calls(conn, response_obj.tool_calls)
            messages.extend(tool_messages)
            
            # Get next response after tool execution
            with console.status("[bold blue]Processing results...[/bold blue]", spinner="dots"):
                response = client.chat.completions.create(
                    model=config.MODEL_NAME,
                    messages=messages,
                    tools=TOOLS,
                )
            response_obj = response.choices[0].message
        
        # Display final response
        display_assistant_response(response_obj)
        
        # Add final response to history
        messages.append(response_obj)
    
    print('\n\nGoodbye!\n\n')


def main() -> None:
    """Main entry point for the chatbot."""
    conn = setup_database()
    client = setup_llm_client()
    system_prompt_message = load_system_prompt()
    
    run_chat_loop(conn, client, system_prompt_message)


if __name__ == '__main__':
    main()
    