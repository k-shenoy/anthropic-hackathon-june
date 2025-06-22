
from safetytooling.utils import utils
from safetytooling.apis import InferenceAPI
from safetytooling.data_models import ChatMessage, Prompt, MessageRole
import os
import sys
import pathlib


from src.utils import load_prompt_file, get_project_root

utils.setup_environment(
    openai_tag="OPENAI_API_KEY",
    anthropic_tag="ANTHROPIC_API_KEY",
)

def add_to_python_path(*relative_paths: str) -> None:    
    """
    Add multiple paths to Python path relative to the repository root.
    Repository root is assumed to be one level up from the notebooks directory.
    """
    notebook_dir = pathlib.Path(os.getcwd())
    repo_root = notebook_dir.parent if notebook_dir.name == "notebooks" else notebook_dir

    for path in relative_paths:
        full_path = repo_root / path
        if full_path.exists():
            if str(full_path) not in sys.path:
                sys.path.append(str(full_path))
        else:
            print(f"Warning: Path {full_path} does not exist")


