import json
import time
import asyncio
import pathlib
from typing import List, Dict, Any

from safetytooling.apis import InferenceAPI
from safetytooling.data_models import ChatMessage, MessageRole, Prompt
from safetytooling.utils import utils

utils.setup_environment()

HOME_DIR = pathlib.Path.home()
API = InferenceAPI(cache_dir=HOME_DIR / ".cache")

async def generate_transcript(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Generate transcript for a single dataset entry using GPT-4.1."""
    
    system_prompt = entry.get("system_prompt", "")
    user_prompts = entry.get("user_prompts", [])
    
    if not user_prompts:
        return {"error": "No user prompts found"}
    
    # Initialize conversation
    messages = []
    if system_prompt:
        messages.append(ChatMessage(content=system_prompt, role=MessageRole.system))
    
    transcript = {
        "original_entry": entry,
        "conversation": [],
        "metadata": {
            "model": "gpt-4.1-2025-04-14",
            "timestamp": time.time()
        }
    }
    
    try:
        # Process each user prompt sequentially
        for i, user_prompt in enumerate(user_prompts):
            # Add user message
            messages.append(ChatMessage(content=user_prompt, role=MessageRole.user))
            transcript["conversation"].append({"role": "user", "content": user_prompt})
            
            # Create prompt and get response
            prompt = Prompt(messages=messages)
            response = await API(
                model_id="gpt-4.1-2025-04-14",
                prompt=prompt,
                max_attempts_per_api_call=1,
            )
            
            assistant_response = response.completion
            
            # Add assistant response to messages and transcript
            messages.append(ChatMessage(content=assistant_response, role=MessageRole.assistant))
            transcript["conversation"].append({"role": "assistant", "content": assistant_response})
            
            # Add small delay to avoid rate limiting
            await asyncio.sleep(0.5)
            
    except Exception as e:
        transcript["error"] = str(e)
        print(f"Error processing entry {entry.get('question', 'unknown')}: {e}")
    
    return transcript

async def generate_transcripts_batch(dataset: List[Dict[str, Any]], limit: int = None) -> List[Dict[str, Any]]:
    """Generate transcripts for a batch of dataset entries."""
    
    if limit:
        dataset = dataset[:limit]
    
    transcripts = []
    
    for i, entry in enumerate(dataset):
        print(f"Processing entry {i+1}/{len(dataset)}: {entry.get('variant_type', 'unknown')}")
        print(f"Question: {entry.get('question', 'N/A')[:100]}...")
        
        transcript = await generate_transcript(entry)
        transcripts.append(transcript)
        
        # Progress update
        if (i + 1) % 5 == 0:
            print(f"Completed {i+1} entries")
    
    return transcripts

def save_transcripts(transcripts: List[Dict[str, Any]], filename: str):
    """Save transcripts to JSON file."""
    with open(filename, 'w') as f:
        json.dump(transcripts, f, indent=2)
    print(f"Saved {len(transcripts)} transcripts to {filename}")

def load_dataset(filename: str) -> List[Dict[str, Any]]:
    """Load dataset from JSON file."""
    with open(filename, 'r') as f:
        return json.load(f)

async def main():
    # Load dataset
    print("Loading dataset...")
    dataset = load_dataset("preference_dataset.json")
    print(f"Loaded {len(dataset)} entries")
    
    # Test with first 10 entries
    print("\nTesting with first 10 entries...")
    test_transcripts = await generate_transcripts_batch(dataset, limit=10)
    
    # Save test results
    save_transcripts(test_transcripts, "test_transcripts.json")
    
    # Print summary
    successful = len([t for t in test_transcripts if "error" not in t])
    failed = len([t for t in test_transcripts if "error" in t])
    
    print(f"\nTest Results:")
    print(f"Successful: {successful}")
    print(f"Failed: {failed}")
    
    if test_transcripts:
        print(f"\nSample transcript structure:")
        sample = test_transcripts[0]
        print(f"Variant type: {sample['original_entry']['variant_type']}")
        print(f"Conversation turns: {len(sample['conversation'])}")
        if "conversation" in sample and sample["conversation"]:
            print(f"First user message: {sample['conversation'][0]['content'][:100]}...")
            if len(sample["conversation"]) > 1:
                print(f"First assistant response: {sample['conversation'][1]['content'][:100]}...")

if __name__ == "__main__":
    asyncio.run(main())