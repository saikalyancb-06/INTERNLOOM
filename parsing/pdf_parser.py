try:
    import fitz  # PyMuPDF
    import pdfplumber
    import numpy as np
    import easyocr
except ModuleNotFoundError as e:
    print(f"\n[ERROR] Missing dependency: {e}")
    print("Please make sure you have activated your virtual environment or installed dependencies using:")
    print("    pip install -r requirements.txt\n")
    import sys
    sys.exit(1)
import os

# Initialize EasyOCR reader lazily to save startup time/memory
_ocr_reader = None

def get_ocr_reader():
    global _ocr_reader
    if _ocr_reader is None:
        # Download models if needed, using english language, suppressing progress print encoding errors
        _ocr_reader = easyocr.Reader(['en'], gpu=False, verbose=False)
    return _ocr_reader

def is_scanned_pdf(pdf_path):
    """
    Check if the PDF is scanned by verifying word count.
    If the extracted text word count is very low (< 50 words), return True.
    """
    try:
        doc = fitz.open(pdf_path)
        total_words = 0
        for page in doc:
            text = page.get_text()
            words = text.split()
            total_words += len(words)
        doc.close()
        return total_words < 50
    except Exception:
        return True

def extract_scanned_pdf(pdf_path):
    """
    Rasterise pages using PyMuPDF and perform OCR using EasyOCR.
    """
    text_content = []
    try:
        doc = fitz.open(pdf_path)
        reader = get_ocr_reader()
        for page_num in range(len(doc)):
            page = doc[page_num]
            pix = page.get_pixmap(dpi=150)
            img_data = pix.tobytes("png")
            # Run EasyOCR
            results = reader.readtext(img_data)
            # Sort OCR results by top-to-bottom, left-to-right
            results.sort(key=lambda r: (r[0][0][1], r[0][0][0]))
            page_text = " ".join([res[1] for res in results])
            text_content.append(page_text)
        doc.close()
        return "\n".join(text_content), "OCR"
    except Exception as e:
        return "", f"OCR_FAILED: {str(e)}"

def detect_and_parse_columns(page):
    """
    Detect if the page has a two-column layout and parse it column-by-column.
    """
    width = page.width
    height = page.height
    words = page.extract_words()
    
    if not words:
        return ""
    
    # We cluster word x0 values to check for two-column structure.
    # A typical two column layout has a gap/gutter near the middle.
    left_words = []
    right_words = []
    midpoint = width / 2
    
    # Let's check if there is a gap around the center
    # For a page width W, gutter could be between 0.4 * W and 0.6 * W
    gutter_start = width * 0.45
    gutter_end = width * 0.55
    
    in_left = 0
    in_right = 0
    
    for w in words:
        if w['x1'] <= midpoint:
            in_left += 1
        elif w['x0'] >= midpoint:
            in_right += 1
            
    # If there are substantial words on both left and right sides of the midpoint,
    # we treat it as a two-column page.
    total_words = len(words)
    if total_words > 20 and in_left / total_words > 0.20 and in_right / total_words > 0.20:
        # Sort left words and right words separately by top, then x0
        left_words_list = [w for w in words if w['x0'] < midpoint]
        right_words_list = [w for w in words if w['x0'] >= midpoint]
        
        # Helper to group words into lines based on top coordinate similarity
        def reconstruct_column_text(col_words):
            if not col_words:
                return ""
            # Sort by top
            col_words.sort(key=lambda w: (w['top'], w['x0']))
            lines = []
            current_line = []
            last_top = None
            
            for w in col_words:
                if last_top is None:
                    last_top = w['top']
                    current_line.append(w)
                elif abs(w['top'] - last_top) < 5:  # words on same line
                    current_line.append(w)
                else:
                    # Sort current line by x0
                    current_line.sort(key=lambda x: x['x0'])
                    lines.append(" ".join([x['text'] for x in current_line]))
                    current_line = [w]
                    last_top = w['top']
            if current_line:
                current_line.sort(key=lambda x: x['x0'])
                lines.append(" ".join([x['text'] for x in current_line]))
            return "\n".join(lines)
            
        left_text = reconstruct_column_text(left_words_list)
        right_text = reconstruct_column_text(right_words_list)
        return left_text + "\n" + right_text
    else:
        # Standard layout: sort words primarily by top, then by x0
        words.sort(key=lambda w: (w['top'], w['x0']))
        lines = []
        current_line = []
        last_top = None
        for w in words:
            if last_top is None:
                last_top = w['top']
                current_line.append(w)
            elif abs(w['top'] - last_top) < 5:
                current_line.append(w)
            else:
                current_line.sort(key=lambda x: x['x0'])
                lines.append(" ".join([x['text'] for x in current_line]))
                current_line = [w]
                last_top = w['top']
        if current_line:
            current_line.sort(key=lambda x: x['x0'])
            lines.append(" ".join([x['text'] for x in current_line]))
        return "\n".join(lines)

def extract_text_from_pdf(pdf_path):
    """
    Main PDF parser entrypoint.
    Returns: (text, parse_status, reason)
    """
    if not os.path.exists(pdf_path):
        return "", "Failed", "File not found"
        
    try:
        # 1. OCR Check
        if is_scanned_pdf(pdf_path):
            text, status = extract_scanned_pdf(pdf_path)
            if text:
                return text, "Clean", "OCR Extracted"
            else:
                return "", "Failed", f"Scanned PDF OCR failed: {status}"
                
        # 2. Extract with column awareness
        text_content = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = detect_and_parse_columns(page)
                text_content.append(page_text)
                
        full_text = "\n".join(text_content).strip()
        if len(full_text.split()) < 30:
            # Fallback to OCR if extracted text is too short (possible vector graphic text or bad parser output)
            text, status = extract_scanned_pdf(pdf_path)
            if text:
                return text, "Clean", "OCR Extracted Fallback"
            else:
                return full_text, "Partial", "Few words extracted and OCR fallback failed"
                
        return full_text, "Clean", "Parsed cleanly with column detection"
    except Exception as e:
        return "", "Failed", f"Parsing error: {str(e)}"
