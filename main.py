#!/usr/bin/env python3

from pathlib import Path

from openai import OpenAI
from dotenv import dotenv_values


# Constants
# Paths
PROJECT_DIR: Path = Path('.')
DATA_DIR: Path = PROJECT_DIR / 'data'
SYSTEM_PROMPT_PATH: Path = PROJECT_DIR / 'system-prompt.txt'
# Other 
LLM_API_ENDPOINT: str = 'https://inference.mlmp.ti.bfh.ch/api/v1'
MODEL_NAME: str = 'ollama/gpt-oss:120b'
CONFIG: dict[str, str] = dotenv_values('.env')


# Check .env fields
REQUIRED_DOTENV_FIELDS: str = ['LLM_API_KEY']
for field_name in REQUIRED_DOTENV_FIELDS:
    if field_name not in CONFIG.keys():
        msg = f'''\nOne ore more entries are missing in the .env file. \
            Couldn't find an entry for '{field_name}'.
        {REQUIRED_DOTENV_FIELDS = }
        {CONFIG.keys() = }
        \n'''
        raise KeyError(msg)

# Establish connection with LLM
client = OpenAI(
    base_url=LLM_API_ENDPOINT,
    api_key=CONFIG['LLM_API_KEY']
)

# Load system prompt
assert SYSTEM_PROMPT_PATH.is_file(), f'System prompt is missing. Please save a file with the system prompt at "{SYSTEM_PROMPT_PATH.absolute()}"'
with open(SYSTEM_PROMPT_PATH, 'r') as f:
    system_prompt: str = f.read()


# Main interaction
messages: list[dict[str, str]] = [
    {
        'role': 'system',
        'content': system_prompt,
    }
]
while True:
    # --- User Part --- #
    # Get user prompt
    user_input = input("\n--- USER ---\nPrompt: ")
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
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
    )
    response_reasoning: str = response.choices[0].message.reasoning_content 
    response_content: str = response.choices[0].message.content 
    # Display response
    print(f'\n--- LLM ---\nLLM Reasoning: {response_reasoning}')
    print(f'\nLLM Response: {response_content}')
    # Add LLM response to messages
    llm_message: dict[str, str] = {
        'role': 'user',
        'content': response_content,
    }
    messages.append(llm_message)

print('\n\nGoodbye!\n\n')
