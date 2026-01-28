#!/usr/bin/env python3
"""
Question Paper Generator using LLM

This script reads the downloaded CBSE syllabus and generates question papers
with random questions at different difficulty levels.

This file provides the structure and prompts for LLM-based question generation.
You can integrate this with OpenAI, Anthropic, or other LLM APIs.

Usage:
    python generate_questions.py --class 10 --subject science --difficulty medium
"""

import os
import json
import random
import argparse
from typing import Dict, List, Optional
from datetime import datetime

SYLLABUS_DIR = "syllabus"
INDEX_FILE = "syllabus_index.json"


class QuestionPaperGenerator:
    """Generate question papers from CBSE syllabus using LLM"""

    DIFFICULTY_LEVELS = {
        "easy": {
            "description": "Basic recall and understanding questions",
            "marks_distribution": {"1_mark": 10, "2_marks": 5, "3_marks": 3},
            "cognitive_level": "Remember, Understand",
        },
        "medium": {
            "description": "Application and analysis questions",
            "marks_distribution": {"1_mark": 5, "2_marks": 8, "3_marks": 5, "5_marks": 2},
            "cognitive_level": "Apply, Analyze",
        },
        "hard": {
            "description": "Evaluation and synthesis questions",
            "marks_distribution": {"2_marks": 5, "3_marks": 8, "5_marks": 4},
            "cognitive_level": "Evaluate, Create",
        },
    }

    def __init__(self, syllabus_dir: str = SYLLABUS_DIR):
        self.syllabus_dir = syllabus_dir
        self.index = self._load_index()

    def _load_index(self) -> Dict:
        """Load the syllabus index"""
        index_path = os.path.join(self.syllabus_dir, INDEX_FILE)
        if os.path.exists(index_path):
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def get_available_classes(self) -> List[int]:
        """Get list of available classes"""
        classes = []
        for key in self.index.get("classes", {}).keys():
            class_num = int(key.replace("class_", ""))
            classes.append(class_num)
        return sorted(classes)

    def get_available_subjects(self, class_num: int) -> List[str]:
        """Get list of available subjects for a class"""
        class_key = f"class_{class_num}"
        class_data = self.index.get("classes", {}).get(class_key, {})
        return list(class_data.get("subjects", {}).keys())

    def load_syllabus(self, class_num: int, subject: str) -> Optional[Dict]:
        """Load syllabus content for a class and subject"""
        class_key = f"class_{class_num}"
        class_data = self.index.get("classes", {}).get(class_key, {})
        subject_data = class_data.get("subjects", {}).get(subject, {})

        json_file = subject_data.get("json_file")
        if json_file and os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return None

    def load_syllabus_markdown(self, class_num: int, subject: str) -> Optional[str]:
        """Load syllabus content as markdown"""
        class_key = f"class_{class_num}"
        class_data = self.index.get("classes", {}).get(class_key, {})
        subject_data = class_data.get("subjects", {}).get(subject, {})

        md_file = subject_data.get("md_file")
        if md_file and os.path.exists(md_file):
            with open(md_file, 'r', encoding='utf-8') as f:
                return f.read()
        return None

    def generate_llm_prompt(
        self,
        class_num: int,
        subject: str,
        difficulty: str = "medium",
        total_marks: int = 80,
        time_duration: str = "3 hours",
        num_sections: int = 4,
    ) -> str:
        """Generate a prompt for LLM to create a question paper"""

        syllabus_content = self.load_syllabus_markdown(class_num, subject)
        if not syllabus_content:
            syllabus_json = self.load_syllabus(class_num, subject)
            if syllabus_json:
                syllabus_content = json.dumps(syllabus_json, indent=2)
            else:
                return "Error: Syllabus not found. Please download the syllabus first."

        difficulty_config = self.DIFFICULTY_LEVELS.get(difficulty, self.DIFFICULTY_LEVELS["medium"])

        prompt = f"""You are an expert CBSE question paper setter. Generate a unique, original question paper based on the following syllabus.

## Instructions:
1. Create ORIGINAL questions - do not copy from existing question papers
2. Ensure questions cover ALL chapters/units proportionally
3. Include a mix of question types: MCQ, Short Answer, Long Answer, Practical/Diagram-based
4. Follow CBSE marking scheme and format
5. Questions should be at {difficulty.upper()} difficulty level
6. Cognitive level focus: {difficulty_config['cognitive_level']}

## Question Paper Details:
- **Class**: {class_num}
- **Subject**: {subject.replace('-', ' ').title()}
- **Total Marks**: {total_marks}
- **Time Duration**: {time_duration}
- **Difficulty**: {difficulty.upper()}
- **Number of Sections**: {num_sections}

## Marks Distribution Suggestion:
{json.dumps(difficulty_config['marks_distribution'], indent=2)}

## CBSE Syllabus Content:
{syllabus_content[:8000]}  # Truncate if too long

## Output Format:
Generate the question paper in the following format:

```
# CBSE CLASS {class_num} {subject.upper().replace('-', ' ')} QUESTION PAPER
## Time: {time_duration} | Total Marks: {total_marks}

### General Instructions:
1. All questions are compulsory.
2. Question paper contains [X] sections.
3. Section A contains MCQs of 1 mark each.
4. Section B contains Short Answer questions of 2 marks each.
5. Section C contains Short Answer questions of 3 marks each.
6. Section D contains Long Answer questions of 5 marks each.

---

### SECTION A (1 Mark Questions)

Q1. [Question text]
    (a) Option A
    (b) Option B
    (c) Option C
    (d) Option D

[Continue with more questions...]

### SECTION B (2 Marks Questions)

Q[X]. [Question text]

[Continue...]

### SECTION C (3 Marks Questions)

Q[X]. [Question text]

[Continue...]

### SECTION D (5 Marks Questions)

Q[X]. [Question text]

---

## ANSWER KEY

[Provide brief answers/key points for each question]
```

Generate a complete, well-balanced question paper now. Make sure each question is UNIQUE and tests different concepts from the syllabus.
"""
        return prompt

    def create_question_paper_request(
        self,
        class_num: int,
        subject: str,
        difficulty: str = "medium",
        **kwargs
    ) -> Dict:
        """Create a complete request object for question paper generation"""

        prompt = self.generate_llm_prompt(class_num, subject, difficulty, **kwargs)

        return {
            "metadata": {
                "class": class_num,
                "subject": subject,
                "difficulty": difficulty,
                "generated_at": datetime.now().isoformat(),
                "request_id": f"qp_{class_num}_{subject}_{difficulty}_{random.randint(1000, 9999)}",
            },
            "prompt": prompt,
            "llm_config": {
                "temperature": 0.7,  # Some creativity for unique questions
                "max_tokens": 4000,
                "top_p": 0.9,
            }
        }

    def save_prompt_to_file(self, class_num: int, subject: str, difficulty: str = "medium"):
        """Save the LLM prompt to a file for manual use"""

        request = self.create_question_paper_request(class_num, subject, difficulty)

        output_dir = os.path.join(self.syllabus_dir, "question_prompts")
        os.makedirs(output_dir, exist_ok=True)

        filename = f"prompt_class{class_num}_{subject}_{difficulty}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        filepath = os.path.join(output_dir, filename)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write("# LLM Prompt for Question Paper Generation\n\n")
            f.write(f"## Metadata\n")
            f.write(json.dumps(request["metadata"], indent=2))
            f.write(f"\n\n## LLM Configuration\n")
            f.write(json.dumps(request["llm_config"], indent=2))
            f.write(f"\n\n## Prompt\n\n")
            f.write(request["prompt"])

        print(f"Prompt saved to: {filepath}")
        return filepath


def main():
    parser = argparse.ArgumentParser(description="Generate CBSE Question Papers using LLM")
    parser.add_argument("--class", dest="class_num", type=int, help="Class number (1-12)")
    parser.add_argument("--subject", type=str, help="Subject name")
    parser.add_argument("--difficulty", type=str, default="medium", choices=["easy", "medium", "hard"])
    parser.add_argument("--list-classes", action="store_true", help="List available classes")
    parser.add_argument("--list-subjects", type=int, help="List subjects for a class")
    parser.add_argument("--save-prompt", action="store_true", help="Save prompt to file")

    args = parser.parse_args()

    generator = QuestionPaperGenerator()

    if args.list_classes:
        classes = generator.get_available_classes()
        print("Available Classes:")
        for c in classes:
            print(f"  - Class {c}")
        return

    if args.list_subjects:
        subjects = generator.get_available_subjects(args.list_subjects)
        print(f"Available Subjects for Class {args.list_subjects}:")
        for s in subjects:
            print(f"  - {s}")
        return

    if args.class_num and args.subject:
        if args.save_prompt:
            generator.save_prompt_to_file(args.class_num, args.subject, args.difficulty)
        else:
            prompt = generator.generate_llm_prompt(args.class_num, args.subject, args.difficulty)
            print(prompt)
    else:
        parser.print_help()
        print("\n" + "="*60)
        print("Example Usage:")
        print("="*60)
        print("1. List available classes:")
        print("   python generate_questions.py --list-classes")
        print("\n2. List subjects for a class:")
        print("   python generate_questions.py --list-subjects 10")
        print("\n3. Generate prompt for Class 10 Science (Medium difficulty):")
        print("   python generate_questions.py --class 10 --subject science --difficulty medium")
        print("\n4. Save prompt to file:")
        print("   python generate_questions.py --class 10 --subject science --save-prompt")


if __name__ == "__main__":
    main()
