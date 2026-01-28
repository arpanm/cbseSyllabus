# CBSE Syllabus Downloader & Question Paper Generator

A Python-based tool to download CBSE syllabus from various educational websites and generate LLM-powered question papers with different difficulty levels.

## Features

- Downloads CBSE syllabus for Classes 1-12 across multiple subjects
- Stores syllabus as both Markdown (`.md`) and JSON (`.json`) files
- Includes sample syllabus data for immediate testing
- Generates LLM prompts for question paper creation
- Supports three difficulty levels: Easy, Medium, Hard
- Structured format optimized for LLM consumption

## Project Structure

```
cbseSyllabus/
├── README.md
├── requirements.txt
├── download_syllabus.py      # Main scraper script
├── generate_questions.py     # Question paper generator
└── syllabus/                 # Downloaded syllabus storage
    ├── syllabus_index.json   # Master index of all syllabi
    ├── class_10/
    │   ├── class_10_science_syllabus.md
    │   ├── class_10_science_syllabus.json
    │   ├── class_10_maths_syllabus.md
    │   └── class_10_maths_syllabus.json
    └── class_12/
        └── class_12_physics_syllabus.md
```

## Installation

```bash
# Clone the repository
git clone <repository-url>
cd cbseSyllabus

# Install dependencies
pip install -r requirements.txt
```

## Usage

### 1. Download Syllabus

```bash
# Download all CBSE syllabus (Classes 1-12, all subjects)
python download_syllabus.py
```

**Note:** Some websites may block automated requests. The script includes:
- Rate limiting and random delays
- Multiple user-agent rotation
- Retry logic with exponential backoff

### 2. Generate Question Papers

```bash
# List available classes
python generate_questions.py --list-classes

# List subjects for a specific class
python generate_questions.py --list-subjects 10

# Generate LLM prompt for question paper
python generate_questions.py --class 10 --subject science --difficulty medium

# Save prompt to file
python generate_questions.py --class 10 --subject science --difficulty hard --save-prompt
```

### 3. Using with LLM APIs

The generated prompts can be used with any LLM API (OpenAI, Anthropic, etc.):

```python
from generate_questions import QuestionPaperGenerator

generator = QuestionPaperGenerator()

# Create a request object with prompt and configuration
request = generator.create_question_paper_request(
    class_num=10,
    subject="science",
    difficulty="medium",
    total_marks=80,
    time_duration="3 hours"
)

# Use the prompt with your preferred LLM
prompt = request["prompt"]
# Send to LLM API...
```

## Sample Data

The repository includes sample syllabus data for:
- Class 10 Science (Complete with all chapters and practicals)
- Class 10 Mathematics (Complete with formulas and theorems)
- Class 12 Physics (Complete with derivations and numericals)

## Syllabus Format

### Markdown Format (`.md`)
Human-readable format with:
- Unit-wise breakdown
- Chapter topics
- Key formulas
- Marking scheme
- Important topics

### JSON Format (`.json`)
Structured format for programmatic access:
```json
{
  "class": 10,
  "subject": "Science",
  "units": [
    {
      "unit_number": 1,
      "unit_name": "Chemical Substances",
      "marks": 25,
      "chapters": [...]
    }
  ]
}
```

## Difficulty Levels

| Level | Description | Question Types |
|-------|-------------|----------------|
| Easy | Basic recall and understanding | MCQs, Fill in blanks, True/False |
| Medium | Application and analysis | Short answers, Diagrams, Numericals |
| Hard | Evaluation and synthesis | Long answers, Case studies, HOTS |

## Configuration

Edit `download_syllabus.py` to customize:
- `OUTPUT_DIR`: Output directory for downloaded files
- `CLASS_SYLLABUS_URLS`: URLs for class-wise syllabus
- `SUBJECT_SYLLABUS_URLS`: URLs for subject-wise syllabus
- `HEADERS`: Custom request headers

## Troubleshooting

### 403 Forbidden Errors
- The website may block automated requests
- Try running the script during off-peak hours
- Consider using a VPN or different network
- Use browser-based scraping with Selenium (see advanced usage)

### Missing Content
- Some pages may have different HTML structures
- Check the `failed_urls` in `syllabus_index.json`
- Manually download from the website if needed

## Contributing

1. Fork the repository
2. Add support for new educational websites
3. Improve content extraction logic
4. Submit a pull request

## License

MIT License

## Disclaimer

This tool is for educational purposes only. Please respect the terms of service of the websites being scraped. The syllabus content is sourced from publicly available educational websites.
