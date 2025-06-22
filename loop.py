
import os
import pathlib
import sys
import json
import dataclasses
from typing import List, Dict, Any, Optional


def put_submodule_in_python_path(submodule_name: str):
    repo_root = pathlib.Path(os.getcwd())
    submodule_path = repo_root / submodule_name
    if submodule_path.exists():
        sys.path.append(str(submodule_path))

put_submodule_in_python_path("safety-tooling")

from safetytooling.apis import InferenceAPI
from safetytooling.data_models import ChatMessage, MessageRole, Prompt
from safetytooling.utils import utils
from safetytooling.utils.experiment_utils import ExperimentConfigBase

utils.setup_environment()
# note: you can change the openai or anthropic tag to use a different API key in .env
# e.g. to use OPENAI_API_KEY1, pass openai_tag="OPENAI_API_KEY1"
# or to use ANTHROPIC_API_KEY_BATCH, pass anthropic_tag="ANTHROPIC_API_KEY_BATCH"

HOME_DIR = pathlib.Path.home()

from agents import Agent, ModelSettings, function_tool, Runner, trace

async def main():
    agent = Agent(name="Assistant", instructions="Reply very concisely.")

    with trace(workflow_name="Conversation", group_id=1):
        # First turn
        result = await Runner.run(agent, "What city is the Golden Gate Bridge in?")
        print(result.final_output)
        # San Francisco

        # Second turn
        new_input = result.to_input_list() + [{"role": "user", "content": "What state is it in?"}]
        result = await Runner.run(agent, new_input)
        print(result.final_output)
        # California

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())