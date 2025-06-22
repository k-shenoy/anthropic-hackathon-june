import re
from dataclasses import dataclass
from typing import List, Optional, Protocol

from safetytooling.apis import InferenceAPI
from safetytooling.data_models import ChatMessage, MessageRole, Prompt

from src.utils import get_project_root, load_prompt_file


@dataclass
class ConversationResult:
    """Container for conversation results"""

    agent_transcript: "Transcript"
    auditor_transcript: "Transcript"
    num_turns_completed: int


class Transcript:
    """Manages conversation history with validation"""

    def __init__(self, system_prompt: str):
        self.messages = [ChatMessage(role=MessageRole.system, content=system_prompt)]

    def add_user_message(self, user_message: str) -> None:
        """Add a user message to the transcript"""
        self.messages.append(ChatMessage(role=MessageRole.user, content=user_message))

    def add_assistant_message(self, assistant_message: str) -> None:
        """Add an assistant message to the transcript"""
        self.messages.append(ChatMessage(role=MessageRole.assistant, content=assistant_message))

    def __len__(self) -> int:
        """Return number of conversation turns (excluding system message)"""
        return (len(self.messages) - 1) // 2

    def get_prompt(self, assistant_prefill: str = None) -> Prompt:
        """Get prompt object for API calls"""
        if assistant_prefill is not None:
            messages = self.messages + [ChatMessage(role=MessageRole.assistant, content=assistant_prefill.strip())]
        else:
            messages = self.messages
        return Prompt(messages=messages)

    def get_last_assistant_message(self) -> Optional[str]:
        """Get the most recent assistant message"""
        for message in reversed(self.messages):
            if message.role == MessageRole.assistant:
                return message.content
        return None


class ConversationParticipant:
    """Base class for conversation participants (Auditor/Agent)"""

    def __init__(
        self,
        name: str,
        model_id: str,
        api: InferenceAPI,
        system_prompt: str,
        **api_kwargs,
    ):
        self.name = name
        self.model_id = model_id
        self.api = api
        self.system_prompt = system_prompt
        self.api_kwargs = api_kwargs
        self.transcript = Transcript(system_prompt)

    async def _generate_response(self, user_message: str, assistant_prefill: str = None) -> str:
        """Generate response using the API"""
        self.transcript.add_user_message(user_message)
        prompt = self.transcript.get_prompt(assistant_prefill)
        response = await self.api(prompt=prompt, model_id=self.model_id, **self.api_kwargs)

        if assistant_prefill is None:
            completion = response[0].completion
        else:
            completion = assistant_prefill + response[0].completion

        self.transcript.add_assistant_message(completion)
        return completion


class Auditor(ConversationParticipant):
    """Auditor that initiates and guides conversations"""

    def __init__(self, model_id: str, api: InferenceAPI, system_prompt: str, **kwargs):
        super().__init__(name="Auditor", model_id=model_id, api=api, system_prompt=system_prompt, **kwargs)

    async def run_step(self, previous_turn_response: Optional[str]) -> str:
        """Run one auditing step"""
        if previous_turn_response is None:
            user_message = "Start the conversation with your first auditing turn"
        else:
            user_message = previous_turn_response

        output = await self._generate_response(user_message)
        return output


class Agent(ConversationParticipant):
    """Agent that responds to auditor prompts"""

    def __init__(
        self,
        name: str,
        model_id: str,
        api: InferenceAPI,
        system_prompt: str,
        **kwargs,
    ):
        super().__init__(name=name, model_id=model_id, api=api, system_prompt=system_prompt, **kwargs)

    async def run_step(
        self,
        previous_turn_response: str,
        assistant_prefill: str = None,
    ) -> str:
        """Run one agent response step"""
        return await self._generate_response(previous_turn_response, assistant_prefill)


class AuditingLoop:
    """Orchestrates conversation between auditor and agent"""

    def __init__(self, auditor: Auditor, agent: Agent, num_turns: int):
        self.auditor = auditor
        self.agent = agent
        self.num_turns = num_turns
        self.turns_completed = 0

    async def run(self) -> ConversationResult:
        """Run the full auditing conversation"""
        # Start with auditor
        auditing_output = await self.auditor.run_step(None)
        auditing_prefill = None

        # Alternate between agent and auditor
        for turn in range(self.num_turns):
            agent_output = await self.agent.run_step(
                previous_turn_response=auditing_output,
                assistant_prefill=auditing_prefill,
            )
            self.turns_completed = turn + 1

            # Don't run auditor on the last turn
            if turn < self.num_turns - 1:
                auditing_output = await self.auditor.run_step(agent_output)

                # Find and extract prefill content, then remove prefill tags
                prefill_tags = re.findall(r"<prefill>(.*?)</prefill>", auditing_output, re.DOTALL)
                auditing_prefill = prefill_tags[0] if prefill_tags else None
                auditing_output = re.sub(r"<prefill>.*?</prefill>", "", auditing_output, flags=re.DOTALL).strip()

                if auditing_prefill is not None:
                    auditing_prefill = auditing_prefill.replace("<think>", "").replace("</think>", "")
                    auditing_prefill = "<think>\n" + auditing_prefill
                    auditing_prefill = auditing_prefill.strip()

                if "END CONVERSATION" in auditing_output:
                    break

        return ConversationResult(
            agent_transcript=self.agent.transcript,
            auditor_transcript=self.auditor.transcript,
            num_turns_completed=self.turns_completed,
        )
