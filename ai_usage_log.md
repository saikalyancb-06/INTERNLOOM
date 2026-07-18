# AI Usage Log

AI tools (specifically Gemini 3.5 Flash and Claude Code) were used for:
- Initial project structure design and layout of modules.
- Formulating regex patterns for normalising grading scales (CGPA/GPA/percentage) and extracting academic degree details.
- Identifying the underlying DOCX XML structure (`<w:txbxContent>`) for extracting text boxes.
- Writing test scripts for evaluating score determinism and drift across multiple runs.
- Designing parsing strategies for multi-column layout clustering of x0 coordinates.
Total AI-generated code represents ~30% of helper functions, with core parsing, scoring rules, and integration logic designed and verified by the engineer.
