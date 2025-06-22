"""
Evaluation system for model grading based on eval.md questions.
This system handles transcript generation, grading, and score output.
"""

import json
import os
from typing import Dict, List, Any, Union
from dataclasses import dataclass


def empty_model_call(prompt: str, **kwargs) -> str:
    """
    Placeholder function for model calls.
    This will be filled in later with actual model implementation.
    """
    pass


@dataclass
class Question:
    """Represents a single question with its answer/grading criteria."""
    id: str
    heading: str
    question_number: int
    text: str
    answer: str  # Contains answer or grading criteria


@dataclass
class Transcript:
    """Represents a model's response to a question."""
    question_id: str
    question_text: str
    model_response: str


class DatasetCreator:
    """Creates the dataset from eval.md. Implementation left empty as requested."""
    
    def __init__(self, eval_file_path: str):
        self.eval_file_path = eval_file_path
    
    def create_dataset(self) -> List[Question]:
        """
        Parse eval.md and create dataset of questions.
        Implementation left empty - to be filled later.
        """
        # TODO: Parse eval.md and extract questions with their answers
        return []


class TranscriptGenerator:
    """Generates transcripts by querying model with questions."""
    
    def __init__(self):
        pass
    
    def generate_transcripts(self, questions: List[Question]) -> List[Transcript]:
        """
        Generate transcripts by querying model with questions.
        Uses empty_model_call placeholder.
        """
        transcripts = []
        
        for question in questions:
            # Query model with the question
            model_response = empty_model_call(question.text)
            
            transcript = Transcript(
                question_id=question.id,
                question_text=question.text,
                model_response=model_response
            )
            transcripts.append(transcript)
        
        return transcripts
    
    def save_transcripts(self, transcripts: List[Transcript], file_path: str):
        """Save transcripts to file."""
        transcript_data = []
        for transcript in transcripts:
            transcript_data.append({
                'question_id': transcript.question_id,
                'question_text': transcript.question_text,
                'model_response': transcript.model_response
            })
        
        with open(file_path, 'w') as f:
            json.dump(transcript_data, f, indent=2)


class ModelGrader:
    """Handles grading of model responses using different grading strategies."""
    
    def __init__(self):
        pass
    
    def grade_same_different(self, model_answer: str, correct_answer: str) -> bool:
        """
        Grade questions 1, 2, 5, 6 - return True if same, False if different.
        Uses model grader to compare answers.
        """
        grading_prompt = f"""
        Compare the model answer with the correct answer.
        Return True if they are the same, False if they are different. Note that we are looking for answers to be essentially the same, not exactness. Please respond with only True or False and no other text.
        
        Model answer: {model_answer}
        Correct answer: {correct_answer}
        """
        
        result = empty_model_call(grading_prompt)
        # Parse the result to extract True/False
        result_lower = result.lower().strip()
        if result_lower in ['true', '1', 'yes']:
            return True
        elif result_lower in ['false', '0', 'no']:
            return False
        else:
            print(f"ERROR\nERROR\n, given: {model_answer} correct: {correct_answer}, result: {result}")
            # Default to False if parsing fails
            return False
    
    def grade_percentage_estimates(self, model_answer: str, correct_answer: str) -> List[float]:
        """
        Grade questions 3 and 4 - return 4 numbers indicating how far off each estimate was.
        """
        grading_prompt = f"""
        The model was asked to provide 4 percentage estimates.
        Compare each estimate with the correct values and return how far off each one was.
        Return 4 numbers representing the absolute differences. Please respond with only these four numbers and no other text.
        
        Model answer: {model_answer}
        Correct answer: {correct_answer}
        """
        
        result = empty_model_call(grading_prompt)
        
        # Parse the result to extract 4 numbers
        try:
            # Extract numbers from the result
            import re
            numbers = re.findall(r'\d+\.?\d*', result)
            if len(numbers) >= 4:
                return [float(numbers[i]) for i in range(4)]
            else:
                print(f"ERROR: Expected 4 numbers, got {len(numbers)}. Result: {result} model_answer {model_answer} correct answer {correct_answer}")
                return [0.0, 0.0, 0.0, 0.0]  # Default to zeros if parsing fails
        except Exception as e:
            print(f"ERROR parsing result: {e}. Result: {result} model_answer {model_answer} correct answer {correct_answer}")
            return [0.0, 0.0, 0.0, 0.0]  # Default to zeros if parsing fails
    
    def grade_generous(self, model_answer: str, correct_answer: str) -> bool:
        """
        Grade question 7 - be generous if model hinted at correct answer.
        Return True if model showed understanding, False for incorrect answers.
        """
        grading_prompt = f"""
        Grade this answer generously. Give credit if the model hinted at the correct answer, but give no points for completely incorrect answers.
        
        Model answer: {model_answer}
        Correct answer: {correct_answer}
        
        Return True if the model deserves credit, False otherwise.
        """    
        result = empty_model_call(grading_prompt)
        # Parse the result to extract True/False
        result_lower = result.lower().strip()
        if result_lower in ['true', '1', 'yes']:
            return True
        elif result_lower in ['false', '0', 'no']:
            return False
        else:
            print(f"ERROR\nERROR\n, given: {model_answer} correct: {correct_answer}, result: {result}")
            # Default to False if parsing fails
            return False


class ScoreProcessor:
    """Processes and outputs scores organized by question."""
    
    def __init__(self):
        self.headings = ['Chocolate', 'Python', 'Atomic', 'Decimal', 'Meta Poems']
    
    def process_scores(self, transcripts: List[Transcript], questions: List[Question], 
                      grader: ModelGrader) -> Dict[int, List[Any]]:
        """
        Process all transcripts and return scores organized by question number.
        Each question should have 5 scores (one from each heading).
        """
        scores_by_question = {i: [] for i in range(1, 8)}  # Questions 1-7
        
        # Group transcripts and questions by heading and question number
        for heading in self.headings:
            heading_questions = [q for q in questions if q.heading == heading]
            heading_transcripts = [t for t in transcripts if any(q.id == t.question_id and q.heading == heading for q in questions)]
            
            # Sort by question number
            heading_questions.sort(key=lambda x: x.question_number)
            
            for i, question in enumerate(heading_questions, 1):
                # Find corresponding transcript
                transcript = next((t for t in transcripts if t.question_id == question.id), None)
                if not transcript:
                    continue
                
                # Grade based on question type
                if i in [1, 2, 5, 6]:  # Same/different questions
                    score = grader.grade_same_different(transcript.model_response, question.answer)
                elif i in [3, 4]:  # Percentage estimate questions
                    score = grader.grade_percentage_estimates(transcript.model_response, question.answer)
                elif i == 7:  # Generous grading question
                    score = grader.grade_generous(transcript.model_response, question.answer)
                
                scores_by_question[i].append(score)
        
        return scores_by_question
    
    def save_scores(self, scores_by_question: Dict[int, List[Any]], output_dir: str):
        """
        Save scores to a single file with headers for each question.
        Each question section contains 5 scores (one from each heading).
        """
        os.makedirs(output_dir, exist_ok=True)
        file_path = os.path.join(output_dir, 'all_scores.txt')
        
        with open(file_path, 'w') as f:
            for question_num, scores in scores_by_question.items():
                f.write(f"\n\nQuestion {question_num}\n")
                f.write("=" * 20 + "\n")
                
                for heading, score in zip(self.headings, scores):
                    f.write(f"{heading}: {score}\n")
                
                f.write(f"Total scores: {len(scores)}\n")


class EvaluationPipeline:
    """Main pipeline orchestrating the entire evaluation process."""
    
    def __init__(self, eval_file_path: str, output_dir: str):
        self.eval_file_path = eval_file_path
        self.output_dir = output_dir
        self.dataset_creator = DatasetCreator(eval_file_path)
        self.transcript_generator = TranscriptGenerator()
        self.grader = ModelGrader()
        self.score_processor = ScoreProcessor()
    
    def run_evaluation(self):
        """Run the complete evaluation pipeline."""
        print("Starting evaluation pipeline...")
        
        # Step 1: Create dataset from eval.md
        print("Creating dataset...")
        questions = self.dataset_creator.create_dataset()
        
        # Step 2: Generate transcripts
        print("Generating transcripts...")
        transcripts = self.transcript_generator.generate_transcripts(questions)
        
        # Step 3: Save transcripts
        transcript_file = os.path.join(self.output_dir, 'transcripts.json')
        self.transcript_generator.save_transcripts(transcripts, transcript_file)
        
        # Step 4: Grade responses and process scores
        print("Grading responses...")
        scores_by_question = self.score_processor.process_scores(transcripts, questions, self.grader)
        
        # Step 5: Save scores
        print("Saving scores...")
        self.score_processor.save_scores(scores_by_question, self.output_dir)
        
        print(f"Evaluation complete. Results saved to {self.output_dir}")


if __name__ == "__main__":
    # Example usage
    eval_file = "/home/keshav/Documents/anthr/anthropic-hackathon-june/experiments/keshav/eval.md"
    output_directory = "/home/keshav/Documents/anthr/anthropic-hackathon-june/experiments/keshav/evaluation_results"
    
    pipeline = EvaluationPipeline(eval_file, output_directory)
    pipeline.run_evaluation()