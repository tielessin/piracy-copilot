from pathlib import Path
from dotenv import dotenv_values


# Default Constants
# Paths
PROJECT_DIR: Path = Path('.')
DOTENV_FILE_PATH: Path = PROJECT_DIR / '.env'
DEFAULT_DATA_DIR: Path = PROJECT_DIR / 'data'
DEFAULT_SYSTEM_PROMPT_PATH: Path = PROJECT_DIR / 'system-prompt.txt'
DEFAULT_SAILORS_DATASET_PATH: Path = DEFAULT_DATA_DIR / 'sailors.csv'
DEFAULT_ITEMS_DATASET_PATH: Path = DEFAULT_DATA_DIR / 'items.csv'
DEFAULT_DB_FILE_PATH: Path = DEFAULT_DATA_DIR / 'pirate_data.tmp.duckdb'
# Other 
DEFAULT_LLM_API_ENDPOINT: str = 'https://inference.mlmp.ti.bfh.ch/api/v1'
DEFAULT_MODEL_NAME: str = 'ollama/gpt-oss:120b'


# Load .env file
_env = dotenv_values(DOTENV_FILE_PATH)


# Apply overrides from .env
_defaults = {k: v for k, v in globals().items() if k.startswith('DEFAULT_')}
for default_name, default_value in _defaults.items():
    const_name = default_name.replace('DEFAULT_', '', 1)
    env_value = _env.get(const_name)
    
    if env_value is not None:
        # Cast to same type as default
        const_type = type(default_value)
        globals()[const_name] = const_type(env_value)
    else:
        globals()[const_name] = default_value


# Required .env variables (no defaults)
LLM_API_KEY: str = _env.get('LLM_API_KEY', 'NO API KEY HAS BEEN PROVIDED')
if LLM_API_KEY == 'NO API KEY HAS BEEN PROVIDED':
    raise ValueError(f'''No llm api key provided (-> LLM_API_KEY field in .env file is missing). Solution:
                     1) Get an API key for the LLM you want to use if you don't have one yet
                     2) Open (or create if it doesn't exist) the .env file at {DOTENV_FILE_PATH.absolute()}
                     3) Add a line in the .env file with the key-value pair. It should look something like `LLM_API_KEY=sk-bfaf01ca94d9e566fa48bb4a82c15e95`
                     4) If you did it correctly, it should fix this issue and you shouldn't see this error next time.
                     \n\n''')
