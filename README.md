# InternLoom Resume Shortlisting Engine

InternLoom is a fully automated, two-stage Resume Shortlisting Engine. It extracts structured candidate profiles from unstructured PDF, DOCX, TXT, and XML files (handling multi-columns, tables, text boxes, and scanned pages using OCR) and scores/ranks candidates against job descriptions.

---

## 🚀 Setup Instructions

1. **Initialize & Activate Environment**:
   ```bash
   python -m venv .venv
   # Windows PowerShell:
   .\.venv\Scripts\Activate.ps1
   # Windows Command Prompt:
   .\.venv\Scripts\activate.bat
   # Linux/macOS:
   source .venv/bin/activate
   ```
2. **Install Pinned Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```
   *(Note: Torch and PyMuPDF will be installed automatically from this file).*

---

## ⚡ Run in Under 5 Minutes Examples

### 1. Judge Mode: Single Resume Quick Test (`demo_single.py`)
Evaluate a single candidate resume against a role and print a formatted evaluation report directly to the terminal:
```bash
# Evaluate a PDF resume against a default role key
python demo_single.py resumes/scanned_resume_test.pdf --jd frontend_developer

# Evaluate a DOCX resume against a raw, comma-separated skill list
python demo_single.py resumes/SDE_A.docx --jd "Python, JavaScript, SQL, Django"
```

### 2. Bulk Evaluation CLI (`main.py`)
Run the parser pipeline on the entire default `resumes/` folder against the `frontend_developer` role:
```bash
python main.py --input resumes --jd frontend_developer --output output_results
```
This generates three files under `output_results/`:
1. `frontend_developer_results.md` - Executive summary with shortlisted candidates, reserve candidates, and disqualification metrics.
2. `frontend_developer_results.json` - Queryable structured dataset.
3. `parse_quality_report.md` - Parse quality status for all evaluated files.

---

## 🌐 Launch the Streamlit Web Application

To run the interactive UI dashboard:
```bash
streamlit run app.py
```
This launches a browser session at **[http://localhost:8501](http://localhost:8501)** where you can:
1. **Bulk Shortlist**: Drag-and-drop `.zip` files containing mixed-format resumes to parse, score, and inspect Ranked/Reserve/Unqualified tables.
2. **Role Recommender**: Upload a single resume to instantly see a career suitability leaderboard scored against all 5 target JDs.

---

## 📂 Deliverables Directory (`sample_outputs/`)
All baseline runs, score stability checks, and edge-case evaluations are structured in the repository:
* `sample_outputs/` - Standard output reports for the 5 target JDs.
* `sample_outputs/ocr_scanned_resume_demo/` - OCR parser extraction logs.
* `sample_outputs/inferred_role_check/` - Plain text JD role inference logs.
* `sample_outputs/unreliable_jd_check/` - Warning and low-confidence overrides for JDs without skills.
* `sample_outputs/vague_jd_check/` - Performance against vague job descriptions.
* `sample_outputs/ds_intern_check/` - Robustness check using a custom 6th JD.
* `sample_outputs/determinism_check_run_1 / 2 / 3` - Outputs verifying 0.0 score drift.
