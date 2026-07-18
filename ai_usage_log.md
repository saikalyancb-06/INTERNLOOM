# AI Usage Log

We used Gemini 1.5 Pro and Claude 3.5 Sonnet to assist with:
* Regex generation for normalising grading scales (CGPA/GPA/percentages) and extracting emails/contacts.
* Identifying DOCX XML structures (`<w:txbxContent>`) for text box extraction.
* Bootstrapping the initial Streamlit layout and standardizing CSS resets.

Beyond the baseline generation, we custom-implemented:
* A multi-column parsing heuristic clustering text bounds by x0 coordinates.
* A robust candidate deduplication algorithm grouping by email or name/college with custom score/parse tie-breakers, plus Failed and low-signal Partial parse bypasses.
* A fallback parser that infers required skills from default JDs via role keywords when no skills are matched.
* A DRY CLI judge mode wrapper (`demo_single.py`) reusing parsing/scoring modules.
* An automated determinism validation suite (`test_engine.py`) confirming absolute zero score drift across consecutive runs.


