# InternLoom Resume Shortlisting Engine

InternLoom is a fully automated, two-stage Resume Shortlisting Engine. It extracts structured candidate profiles from unstructured PDF and DOCX files (handling multi-columns, tables, text boxes, and scanned pages) and scores/ranks candidates against job descriptions.

## Setup Instructions

1. Install requirements:
   ```bash
   pip install -r requirements.txt
   ```
2. Ensure you have PyTorch installed (required by EasyOCR fallback).

## Run in Under 5 Minutes Example

Run shortlisting on the default `resumes/` folder against the `frontend_developer` role and output results to `output_results/`:

```bash
python main.py --input resumes --jd frontend_developer --output output_results
```

This generates three files:
1. `output_results/frontend_developer_results.md` - Clean markdown report with Shortlist, Reserve list, and Failed parses.
2. `output_results/frontend_developer_results.json` - Queryable structured dataset.
3. `output_results/parse_quality_report.md` - Tracking parse status for all processed files.

## Running Custom Job Descriptions

You can pass a raw plain English job description directly or path to a text/JSON file:

```bash
# Path to unstructured text file
python main.py --input resumes --jd path/to/job_desc.txt --output custom_results

# Direct plain English text
python main.py --input resumes --jd "Frontend Engineer with 2+ years React.js and CSS. Preferred TypeScript. CGPA Min 7.0" --output custom_results
```
