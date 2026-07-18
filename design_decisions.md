# Design Decisions

### 1. Handling Multi-Column PDF Layouts
Naive top-to-bottom text readers merge multi-column text horizontally, creating a jumbled mess ("column-bleed"). To prevent this, our engine uses `pdfplumber` to analyze word positions on each page. It checks the distribution of the horizontal starting coordinates (`x0`) of all words. If it detects a substantial concentration of text on both the left and right sides of the page midpoint (width / 2) with a distinct vertical divider space, it treats the page as a two-column layout. The parser then isolates coordinates corresponding to the left half and right half, groups and sorts words in each column independently (first by `top` coordinate, then by `x0`), and aggregates them column-by-column.

### 2. Handling Scanned Resumes (No-Text-Layer Fallback)
If a PDF yields fewer than 50 words via standard extraction, the engine flags it as a potential scanned document. Instead of failing silently or crashing, it triggers the automatic OCR fallback. It uses PyMuPDF (`fitz`) to rasterize the PDF pages to high-resolution PNG images at 150 DPI. These images are then passed to `easyocr` (which runs on PyTorch). The text returned is sorted coordinate-wise (top-to-bottom, left-to-right) to reconstruct the layout text. The parse quality for successful OCR runs is marked as `Clean` (flagged with "OCR Extracted" source metadata).

### 3. Extracting Skills from Unlabeled/Inline Text
Candidates rarely list all their skills in a neatly labeled "Skills" section; skills are frequently embedded inline in project descriptions, certificates, and work experience. To extract them comprehensively, the engine normalizes the entire resume text to lowercase and strips special formatting. It then performs a word-boundary-aware search across the entire document text against a config-driven skills synonym map. For example, if "ReactJS", "React.js", or "React" matches, it maps to the canonical skill `react.js`.

### 4. Coupling Parse Quality to Confidence
Parse quality has a direct, hard-coded relationship with scoring confidence:
- **Clean Parse**: All text was extracted successfully. Scoring confidence is evaluated as `High` or `Medium` based on how unambiguously skills matched (e.g. fewer implicit matches or guessed grading scales yield `High`).
- **Partial Parse**: Text was recovered but was extremely short or layout elements were garbled. Confidence is capped at `Medium`, and the candidate's final score is capped at `70.0` maximum to prevent false positives.
- **Failed Parse**: No readable text was recovered or parsing threw unhandled exceptions. In this case, the engine **produces no score at all (set to `null`)**, sets confidence to `Low`, and routes the candidate to a dedicated **Failed Parse & Review Queue** for human verification.

### 5. DOCX Table & Text-Box Parsing
Standard paragraphs in DOCX are read using `docx.Document.paragraphs`. However, resumes designed with Word tables or Canva-style floating text boxes hide content inside complex XML tags. Our engine handles:
- **Tables**: Iterates through tables row-by-row and cell-by-cell. Text inside cells is preserved separately and joined with column dividers (`|`) to maintain structure.
- **Text Boxes**: Standard paragraphs do not extract floating text boxes. Our engine walks the raw XML tree of the DOCX body to find all `<w:txbxContent>` tags, extracting and appending any text inside `<w:t>` tags to ensure no floating layout content is lost.
