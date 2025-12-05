#!/usr/bin/env python3

import sys
from pathlib import Path

from openai import OpenAI
from dotenv import dotenv_values

import rich
from rich.panel import Panel
from rich.text import Text
from rich.markdown import Markdown


# Constants
# Paths
PROJECT_DIR: Path = Path('.')
DATA_DIR: Path = PROJECT_DIR / 'data'
SYSTEM_PROMPT_PATH: Path = PROJECT_DIR / 'system-prompt.txt'
# Other 
LLM_API_ENDPOINT: str = 'https://inference.mlmp.ti.bfh.ch/api/v1'
MODEL_NAME: str = 'ollama/gpt-oss:120b'
CONFIG: dict[str, str] = dotenv_values('.env')


# Init rich print
console = rich.console.Console()

# Check .env fields
REQUIRED_DOTENV_FIELDS: list[str] = ['LLM_API_KEY']
for field_name in REQUIRED_DOTENV_FIELDS:
    if field_name not in CONFIG.keys():
        msg = f"Missing entry for '{field_name}' in .env file."
        console.print(f"[bold red]Error:[/bold red] {msg}")
        sys.exit(1)

# Establish connection with LLM
client = OpenAI(
    base_url=LLM_API_ENDPOINT,
    api_key=CONFIG['LLM_API_KEY']
)

# Load system prompt
if not SYSTEM_PROMPT_PATH.is_file():
    console.print(f"[bold red]Error:[/bold red] System prompt missing at {SYSTEM_PROMPT_PATH.absolute()}")
    sys.exit(1)
with open(SYSTEM_PROMPT_PATH, 'r') as f:
    system_prompt: str = f.read()
system_prompt_message: dict[str, str] = {
    'role': 'system',
    'content': system_prompt,
}


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
        # Handle Ctrl+C gracefully
        break
    # Check if user wants to quit
    if user_input.lower() in ['quit', 'exit']:
        break
    # Add user prompt to messages
    user_message: dict[str, str] = {
        'role': 'user',
        'content': user_input,
    }
    messages.append(user_message)
    
    # --- LLM Part --- #
    # Send prompt (with conversation history) and get response
    with console.status("[bold blue]Thinking...[/bold blue]", spinner="dots"):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
        )
    response_obj = response.choices[0].message
    response_reasoning: str = response_obj.reasoning_content 
    response_content: str = response_obj.content
    
    # Display LLM Response
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
    llm_message: dict[str, str] = {
        'role': 'user',
        'content': response_content,
    }
    messages.append(llm_message)

print('\n\nGoodbye!\n\n')
