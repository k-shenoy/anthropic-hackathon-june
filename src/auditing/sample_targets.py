import re

from safetytooling.apis import InferenceAPI
from safetytooling.data_models import ChatMessage, MessageRole, Prompt
from safetytooling.utils import utils
from tqdm.asyncio import tqdm

from src.utils import get_project_root, load_prompt_file


class TargetBehavior:
    def __init__(
        self,
        behavior_to_analyze: str,
        num_ideas: int = 50,
        model_id: str = "claude-3-5-sonnet-20240620",
        api: InferenceAPI = None,
    ):
        self.behavior_to_analyze = behavior_to_analyze
        self.num_ideas = num_ideas
        self.model_id = model_id
        self.api = api

    def is_valid_formatting(self, response) -> bool:
        """
        Check if the output contains a properly formatted numbered list.
        Allows introductory text before the numbered list.
        """
        # Extract the completion text from the response object
        if hasattr(response, "completion"):
            output = response.completion
        elif hasattr(response, "content"):
            # Handle different response formats
            if isinstance(response.content, list) and len(response.content) > 0:
                # Handle case where content is a list of objects with text attribute
                if hasattr(response.content[0], "text"):
                    output = response.content[0].text
                else:
                    output = str(response.content[0])
            else:
                output = str(response.content)
        elif hasattr(response, "text"):
            output = response.text
        else:
            output = str(response)

        # Debug: Print the output to see what we're working with
        print(f"Debug - Output type: {type(output)}")
        print(f"Debug - Output preview: {output[:200]}...")

        # More comprehensive regex pattern for numbered lists
        # Matches: "1.", "1)", "1 -", "1:", etc. with optional whitespace
        numbered_patterns = [
            r"^\s*(\d+)[\.\)]\s+.+",  # Standard: "1. item" or "1) item"
            r"^\s*(\d+)[\.\):\-]\s+.+",  # Extended: "1: item" or "1- item"
            r"^\s*(\d+)\s+[\-\•]\s+.+",  # Spaced: "1 - item" or "1 • item"
        ]

        numbered_items = []

        # Try each pattern
        for pattern in numbered_patterns:
            matches = re.findall(pattern, output, re.MULTILINE)
            if matches:
                numbered_items = matches
                break

        # If no pattern matched, try a more flexible approach
        if not numbered_items:
            # Look for lines that start with a number followed by any non-alphanumeric character
            flexible_pattern = r"^\s*(\d+)[^\w\s]+.*\S"
            numbered_items = re.findall(flexible_pattern, output, re.MULTILINE)

        # Debug: Print what we found
        print(f"Debug - Found {len(numbered_items)} numbered items")
        if numbered_items:
            print(f"Debug - Number range: {min(map(int, numbered_items))} to {max(map(int, numbered_items))}")

        # Must have at least some numbered lines
        if not numbered_items:
            print("Debug - No numbered items found")
            return False

        # Convert to integers and check for reasonable numbering
        try:
            numbers = [int(num) for num in numbered_items]
            numbers.sort()

            # Check if numbering starts from 1 and is mostly sequential
            if numbers[0] != 1:
                print(f"Debug - Numbering doesn't start from 1, starts from {numbers[0]}")
                return False

            # Allow for some gaps in numbering (up to 20% missing)
            expected_max = max(numbers)
            actual_count = len(numbers)
            if actual_count < expected_max * 0.8:
                print(f"Debug - Too many gaps in numbering: {actual_count} items but max number is {expected_max}")
                return False

        except ValueError:
            print("Debug - Error converting numbers")
            return False

        return True

    def extract_ideas_from_response(self, ideas_str: str) -> list[str]:
        """
        Extract individual ideas from a numbered list response.
        """
        # Try multiple patterns to match numbered items
        patterns = [
            r"^\s*\d+[\.\)]\s+(.+)",  # Standard: "1. item" or "1) item"
            r"^\s*\d+[\.\):\-]\s+(.+)",  # Extended: "1: item" or "1- item"
            r"^\s*\d+\s+[\-\•]\s+(.+)",  # Spaced: "1 - item" or "1 • item"
        ]

        extracted_ideas = []

        # Try each pattern
        for pattern in patterns:
            matches = re.findall(pattern, ideas_str, re.MULTILINE)
            if matches:
                extracted_ideas = matches
                break

        # If no pattern worked, try flexible approach
        if not extracted_ideas:
            flexible_pattern = r"^\s*\d+[^\w\s]+\s*(.+)"
            extracted_ideas = re.findall(flexible_pattern, ideas_str, re.MULTILINE)

        # Clean up the extracted ideas (remove extra whitespace, empty items)
        cleaned_ideas = []
        for idea in extracted_ideas:
            cleaned_idea = idea.strip()
            if cleaned_idea:  # Only add non-empty ideas
                cleaned_ideas.append(cleaned_idea)

        return cleaned_ideas

    async def generate_ideas(self):
        prompt = load_prompt_file(get_project_root() / "prompts" / "automated_auditing" / "idea_generator.jinja2")
        prompt = prompt.replace("{NUM_IDEAS}", str(self.num_ideas)).replace(
            "{BEHAVIOR_TO_ANALYZE}", self.behavior_to_analyze
        )
        ideas = await self.api(
            prompt=Prompt(messages=[ChatMessage(role=MessageRole.user, content=prompt)]),
            model_id=self.model_id,
            is_valid=self.is_valid_formatting,
            temperature=1.0,
        )
        ideas_str = ideas[0].completion

        # Extract the ideas from the numbered list
        extracted_ideas = self.extract_ideas_from_response(ideas_str)
        return extracted_ideas

    def is_valid_system_prompt(self, response) -> bool:
        """
        Check if the output contains a properly formatted system prompt and auditor summary.
        """
        # Extract the completion text from the response object
        if hasattr(response, "completion"):
            output = response.completion
        elif hasattr(response, "content"):
            # Handle different response formats
            if isinstance(response.content, list) and len(response.content) > 0:
                # Handle case where content is a list of objects with text attribute
                if hasattr(response.content[0], "text"):
                    output = response.content[0].text
                else:
                    output = str(response.content[0])
            else:
                output = str(response.content)
        elif hasattr(response, "text"):
            output = response.text
        else:
            output = str(response)

        # Check if it contains both required sections
        system_prompt_pattern = r"\*\*Generated System Prompt:\*\*\s*```(.*?)```"
        auditor_summary_pattern = r"\*\*Auditor Summary:\*\*\s*```(.*?)```"

        system_prompt_match = re.search(system_prompt_pattern, output, re.DOTALL)
        auditor_summary_match = re.search(auditor_summary_pattern, output, re.DOTALL)

        if not system_prompt_match:
            print("Debug - No 'Generated System Prompt:' section found")
            return False

        if not auditor_summary_match:
            print("Debug - No 'Auditor Summary:' section found")
            return False

        # Check that both sections have content
        system_prompt_content = system_prompt_match.group(1).strip()
        auditor_summary_content = auditor_summary_match.group(1).strip()

        if len(system_prompt_content) < 100:  # Minimum reasonable length
            print(f"Debug - System prompt too short: {len(system_prompt_content)} characters")
            return False

        if len(auditor_summary_content) < 50:  # Minimum reasonable length
            print(f"Debug - Auditor summary too short: {len(auditor_summary_content)} characters")
            return False

        return True

    def extract_system_prompt_and_summary(self, output: str) -> tuple[str, str]:
        """
        Extract the system prompt and auditor summary from the formatted response.
        """
        system_prompt_pattern = r"\*\*Generated System Prompt:\*\*\s*```(.*?)```"
        auditor_summary_pattern = r"\*\*Auditor Summary:\*\*\s*```(.*?)```"

        system_prompt_match = re.search(system_prompt_pattern, output, re.DOTALL)
        auditor_summary_match = re.search(auditor_summary_pattern, output, re.DOTALL)

        if not system_prompt_match or not auditor_summary_match:
            raise ValueError("Could not extract system prompt and auditor summary from response")

        system_prompt = system_prompt_match.group(1).strip()
        auditor_summary = auditor_summary_match.group(1).strip()

        return system_prompt, auditor_summary

    async def generate_system_prompt(self, behavior: str, idea: str):
        system_prompt = load_prompt_file(
            get_project_root() / "prompts" / "automated_auditing" / "sys_prompt_generator.jinja2"
        )
        user_inst = f"Behavior: {behavior}\nIdea: {idea}"

        output = await self.api(
            prompt=Prompt(
                messages=[
                    ChatMessage(role=MessageRole.system, content=system_prompt),
                    ChatMessage(role=MessageRole.user, content=user_inst),
                ]
            ),
            model_id=self.model_id,
            is_valid=self.is_valid_system_prompt,
            temperature=1.0,
        )

        output_str = output[0].completion
        system_prompt, auditor_summary = self.extract_system_prompt_and_summary(output_str)
        return system_prompt, auditor_summary

    async def generate_all_environments(self):
        """
        Generate all honeypot environments for the behavior.
        Returns a list of dicts with idea, system_prompt, and auditor_summary.
        Ignores any environments that fail to generate.
        """
        ideas = await self.generate_ideas()

        async def generate_single_environment(idea):
            try:
                system_prompt, auditor_summary = await self.generate_system_prompt(self.behavior_to_analyze, idea)
                return {"idea": idea, "system_prompt": system_prompt, "auditor_summary": auditor_summary}
            except Exception as e:
                print(f"Error generating environment for idea '{idea[:50]}...': {e}")
                return None

        # Create tasks for all ideas
        tasks = [generate_single_environment(idea) for idea in ideas]

        # Execute all tasks concurrently with tqdm.gather for progress bar
        results = await tqdm.gather(*tasks, desc="Generating environments")

        # Filter out None results (failed generations)
        successful_results = [result for result in results if result is not None]

        print(f"Successfully generated {len(successful_results)}/{len(results)} environments")

        return successful_results
