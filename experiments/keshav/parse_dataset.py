import json
import re
import random

def parse_preference_dataset(file_path):
    """Parse the preference dataset markdown file into categorized JSON objects."""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Parse personas
    personas_match = re.search(r'##Personas:(.*?)##', content, re.DOTALL)
    personas = []
    if personas_match:
        personas_text = personas_match.group(1).strip()
        personas = [line.strip() for line in personas_text.split('\n') if line.strip()]
    
    # Parse prepends
    prepends_match = re.search(r'##Prepends(.*?)##', content, re.DOTALL)
    prepends = []
    if prepends_match:
        prepends_text = prepends_match.group(1).strip()
        # Split by commas and clean up
        prepends = [word.strip() for word in prepends_text.replace('\n', ' ').split(',') if word.strip()]
    
    # Parse questions
    questions_match = re.search(r'##Questions:(.*?)Follow-ups:', content, re.DOTALL)
    questions = []
    if questions_match:
        questions_text = questions_match.group(1).strip()
        questions = [line.strip() for line in questions_text.split('\n') if line.strip()]
    
    # Parse follow-ups
    followups_match = re.search(r'Follow-ups:(.*?)Chains:', content, re.DOTALL)
    followups = []
    if followups_match:
        followups_text = followups_match.group(1).strip()
        followups = [line.strip() for line in followups_text.split('\n') if line.strip()]
    
    # Parse chains
    chains_match = re.search(r'Chains:(.*?)$', content, re.DOTALL)
    chains = []
    if chains_match:
        chains_text = chains_match.group(1).strip()
        chains = [line.strip() for line in chains_text.split('\n') if line.strip()]
    
    return {
        "personas": personas,
        "prepends": prepends,
        "questions": questions,
        "followups": followups,
        "chains": chains
    }

def generate_dataset_entry(question, variant_type, **kwargs):
    """Generate a single dataset entry with specified variant."""
    entry = {
        "question": question,
        "variant_type": variant_type,
        "system_prompt": "",
        "user_prompts": [question],
        "metadata": {}
    }
    
    if variant_type == "baseline":
        # No modifications
        pass
    
    elif variant_type == "prepend":
        prepend = kwargs.get("prepend", "")
        entry["user_prompts"] = [f"{prepend} {question}"]
        entry["metadata"]["prepend"] = prepend
    
    elif variant_type == "suffix_number":
        number = kwargs.get("number", random.randint(1000, 9999))
        entry["user_prompts"] = [f"{question} {number}"]
        entry["metadata"]["suffix_number"] = number
    
    elif variant_type == "persona_system":
        persona = kwargs.get("persona", "")
        entry["system_prompt"] = f"You are {persona.lower()}."
        entry["metadata"]["persona"] = persona
    
    elif variant_type == "followup":
        followup = kwargs.get("followup", "")
        entry["user_prompts"] = [question, followup]
        entry["metadata"]["followup"] = followup
    
    elif variant_type == "chain":
        chain = kwargs.get("chain", "")
        next_question = kwargs.get("next_question", "")
        chained_prompt = chain.replace("<Q>", next_question)
        entry["user_prompts"] = [question, chained_prompt]
        entry["metadata"]["chain"] = chain
        entry["metadata"]["next_question"] = next_question
    
    elif variant_type == "chain_followup":
        chain = kwargs.get("chain", "")
        next_question = kwargs.get("next_question", "")
        followup = kwargs.get("followup", "")
        chained_prompt = chain.replace("<Q>", next_question)
        entry["user_prompts"] = [question, chained_prompt, followup]
        entry["metadata"]["chain"] = chain
        entry["metadata"]["next_question"] = next_question
        entry["metadata"]["followup"] = followup
    
    return entry

def generate_full_dataset(data_dict, num_samples_per_variant=10):
    """Generate the full dataset with all variants."""
    dataset = []
    
    questions = data_dict["questions"]
    personas = data_dict["personas"]
    prepends = data_dict["prepends"]
    followups = data_dict["followups"]
    chains = data_dict["chains"]
    
    for question in questions:
        # Baseline questions
        dataset.append(generate_dataset_entry(question, "baseline"))
        
        # Prepend variants
        for _ in range(min(num_samples_per_variant, len(prepends))):
            prepend = random.choice(prepends)
            dataset.append(generate_dataset_entry(question, "prepend", prepend=prepend))
        
        # Suffix number variants
        for _ in range(num_samples_per_variant):
            dataset.append(generate_dataset_entry(question, "suffix_number"))
        
        # Persona system prompt variants
        for persona in personas:
            dataset.append(generate_dataset_entry(question, "persona_system", persona=persona))
        
        # Follow-up variants
        for _ in range(min(num_samples_per_variant, len(followups))):
            followup = random.choice(followups)
            dataset.append(generate_dataset_entry(question, "followup", followup=followup))
        
        # Chain variants
        for chain in chains:
            # Need another question for the chain
            other_questions = [q for q in questions if q != question]
            if other_questions:
                next_question = random.choice(other_questions)
                dataset.append(generate_dataset_entry(question, "chain", 
                                                    chain=chain, next_question=next_question))
        
        # Chain + Follow-up variants (three prompts total)
        for _ in range(min(num_samples_per_variant, len(chains) * len(followups))):
            chain = random.choice(chains)
            followup = random.choice(followups)
            other_questions = [q for q in questions if q != question]
            if other_questions:
                next_question = random.choice(other_questions)
                dataset.append(generate_dataset_entry(question, "chain_followup",
                                                    chain=chain, next_question=next_question, 
                                                    followup=followup))
    
    return dataset

if __name__ == "__main__":
    # Parse the dataset
    data = parse_preference_dataset("preference_dataset.md")
    
    # Save parsed data
    with open("parsed_data.json", "w") as f:
        json.dump(data, f, indent=2)
    
    print("Parsed data structure:")
    for category, items in data.items():
        print(f"{category}: {len(items)} items")
        if items:
            print(f"  Example: {items[0]}")
    
    # Generate full dataset
    dataset = generate_full_dataset(data, num_samples_per_variant=5)
    
    # Save dataset
    with open("preference_dataset.json", "w") as f:
        json.dump(dataset, f, indent=2)
    
    print(f"\nGenerated dataset with {len(dataset)} entries")
    print("\nVariant distribution:")
    variant_counts = {}
    for entry in dataset:
        variant = entry["variant_type"]
        variant_counts[variant] = variant_counts.get(variant, 0) + 1
    
    for variant, count in variant_counts.items():
        print(f"  {variant}: {count}")