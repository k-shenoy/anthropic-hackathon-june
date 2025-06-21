from typing import Optional, List, Protocol
from dataclasses import dataclass
from src.utils import load_prompt_file, get_project_root
from safetytooling.apis import InferenceAPI
from safetytooling.data_models import ChatMessage, Prompt, MessageRole


class ValidationProtocol(Protocol):
    """Protocol for validation functions"""

    def __call__(self, text: str) -> bool: ...


@dataclass
class ConversationResult:
    """Container for conversation results"""

    agent_transcript: "Transcript"
    auditor_transcript: "Transcript"
    num_turns_completed: int


class Transcript:
    """Manages conversation history with validation"""

    def __init__(self, system_prompt: str, validation_fn: Optional[ValidationProtocol] = None):
        self.messages = [ChatMessage(role=MessageRole.system, content=system_prompt)]
        self.validation_fn = validation_fn or (lambda x: True)

    def add_user_message(self, user_message: str) -> None:
        """Add a user message to the transcript"""
        self.messages.append(ChatMessage(role=MessageRole.user, content=user_message))

    def add_assistant_message(self, assistant_message: str) -> None:
        """Add an assistant message to the transcript"""
        self.messages.append(ChatMessage(role=MessageRole.assistant, content=assistant_message))

    def __len__(self) -> int:
        """Return number of conversation turns (excluding system message)"""
        return (len(self.messages) - 1) // 2

    def get_prompt(self) -> Prompt:
        """Get prompt object for API calls"""
        return Prompt(messages=self.messages)

    def is_valid_formatting(self, text: str) -> bool:
        """Check if text meets formatting requirements"""
        return self.validation_fn(text)

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
        validation_fn: Optional[ValidationProtocol] = None,
    ):
        self.name = name
        self.model_id = model_id
        self.api = api
        self.validation_fn = validation_fn
        self.system_prompt = system_prompt
        self.transcript = Transcript(system_prompt, validation_fn)

    async def _generate_response(self, user_message: str) -> str:
        """Generate response using the API"""
        self.transcript.add_user_message(user_message)
        prompt = self.transcript.get_prompt()

        response = await self.api(
            prompt=prompt,
            model_id=self.model_id,
            temperature=1.0,
            #is_valid_formatting=self.transcript.is_valid_formatting,
        )

        completion = response[0].completion
        self.transcript.add_assistant_message(completion)
        return completion


class Auditor(ConversationParticipant):
    """Auditor that initiates and guides conversations"""

    def __init__(
        self, model_id: str, api: InferenceAPI, system_prompt: str, validation_fn: Optional[ValidationProtocol] = None
    ):
        super().__init__(
            name="Auditor", model_id=model_id, api=api, system_prompt=system_prompt, validation_fn=validation_fn
        )

    async def run_step(self, previous_turn_response: Optional[str]) -> str:
        """Run one auditing step"""
        if previous_turn_response is None:
            user_message = "Start the conversation with your first auditing turn"
        else:
            user_message = previous_turn_response

        return await self._generate_response(user_message)


class Agent(ConversationParticipant):
    """Agent that responds to auditor prompts"""

    def __init__(
        self,
        name: str,
        model_id: str,
        api: InferenceAPI,
        system_prompt: str,
        validation_fn: Optional[ValidationProtocol] = None,
    ):
        super().__init__(
            name=name, model_id=model_id, api=api, system_prompt=system_prompt, validation_fn=validation_fn
        )

    async def run_step(self, previous_turn_response: str) -> str:
        """Run one agent response step"""
        return await self._generate_response(previous_turn_response)


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

        # Alternate between agent and auditor
        for turn in range(self.num_turns):
            agent_output = await self.agent.run_step(auditing_output)
            self.turns_completed = turn + 1

            # Don't run auditor on the last turn
            if turn < self.num_turns - 1:
                auditing_output = await self.auditor.run_step(agent_output)

        return ConversationResult(
            agent_transcript=self.agent.transcript,
            auditor_transcript=self.auditor.transcript,
            num_turns_completed=self.turns_completed,
        )
