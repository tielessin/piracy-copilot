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


# Init rich print
console = Console()

# Load data
# You can't use read_only when loading data via CSVs
# We therefore use the CSV files to create a .db file which we then can use in read_only mode
if config.DB_FILE_PATH.is_file():
    # Delete existing to make sure we use the latest version of the csv files for the database
    os.remove(str(config.DB_FILE_PATH))
conn = duckdb.connect(str(config.DB_FILE_PATH))
conn.execute(f"CREATE TABLE sailors AS SELECT * FROM read_csv_auto('{config.SAILORS_DATASET_PATH}')")
conn.execute(f"CREATE TABLE items AS SELECT * FROM read_csv_auto('{config.ITEMS_DATASET_PATH}')")
conn.close()
conn = duckdb.connect(str(config.DB_FILE_PATH), read_only=True)

# Validate required configuration
if not config.LLM_API_KEY:
    console.print(f"[bold red]Error:[/bold red] Missing 'LLM_API_KEY' in .env file.")
    sys.exit(1)

# Establish connection with LLM
client = OpenAI(
    base_url=config.LLM_API_ENDPOINT,
    api_key=config.LLM_API_KEY
)

# Load system prompt
if not config.SYSTEM_PROMPT_PATH.is_file():
    console.print(f"[bold red]Error:[/bold red] System prompt missing at {config.SYSTEM_PROMPT_PATH.absolute()}")
    sys.exit(1)
with open(config.SYSTEM_PROMPT_PATH, 'r') as f:
    system_prompt: str = f.read()
system_prompt_message: dict[str, str] = {
    'role': 'system',
    'content': system_prompt,
}

# Define Tools (LLM Function Calls)
tools: list[dict[str, Any]] = [
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


# Interactions loop
console.print(5 * '\n', end='')
console.print("[bold green]Chat Session Started[/bold green]")
console.print("(Type 'quit' or 'exit' to stop)\n")
messages: list[dict[str, str]] = [system_prompt_message]
while True:
    console.rule("[bold green]User[/bold green]", style="green")
    
    # --- User Part --- #
    # Get user prompt
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
    
    # --- LLM Part --- #
    # Send prompt (with conversation history) and get response
    with console.status("[bold blue]Thinking...[/bold blue]", spinner="dots"):
        response = client.chat.completions.create(
            model=config.MODEL_NAME,
            messages=messages,
            tools=tools,
        )
    response_obj = response.choices[0].message
    
    # Handle tool calls (may need multiple rounds)
    while response_obj.tool_calls:
        # Add assistant message with tool calls to history
        messages.append(response_obj)
        
        # Execute each tool call
        for tool_call in response_obj.tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Display tool call
            console.print(Panel(
                Syntax(function_args['sql'], 'sql', theme='monokai', line_numbers=False),
                title=f"[bold yellow]Tool Call:[/bold yellow] {function_name}",
                border_style="yellow",
                expand=True
            ))
            
            # Execute SQL query
            try:
                result = conn.execute(function_args['sql']).fetchall()
                result_str = json.dumps(result, indent=2, default=str)
            except Exception as e:
                result_str = f"Error executing query: {str(e)}"
            
            # Display result
            console.print(Panel(
                Text(result_str, style="white"),
                title="[bold yellow]Query Result[/bold yellow]",
                border_style="yellow",
                expand=True
            ))
            console.print("")
            
            # Add tool result to messages
            tool_message: dict[str, Any] = {
                'role': 'tool',
                'tool_call_id': tool_call.id,
                'content': result_str,
            }
            messages.append(tool_message)
        
        # Get next response after tool execution
        with console.status("[bold blue]Processing results...[/bold blue]", spinner="dots"):
            response = client.chat.completions.create(
                model=config.MODEL_NAME,
                messages=messages,
                tools=tools,
            )
        response_obj = response.choices[0].message
    
    # Display final LLM response
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
    
    # Add LLM response to messages
    messages.append(response_obj)

print('\n\nGoodbye!\n\n')
