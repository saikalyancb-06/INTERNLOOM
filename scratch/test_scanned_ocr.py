import fitz
import os
import sys

sys.path.append(os.path.abspath("."))
from parsing.pdf_parser import extract_text_from_pdf, is_scanned_pdf

def test_ocr():
    print("=== OCR Verification Test ===")
    pdf_path = "resumes/web_dev__aditya_kulkarni.pdf"
    scanned_path = "scanned_resume_test_3.pdf"
    
    # 1. Create a scanned image-only PDF
    print(f"Creating image-only PDF from {pdf_path}...")
    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=150)
    
    new_doc = fitz.open()
    new_page = new_doc.new_page(width=page.rect.width, height=page.rect.height)
    new_page.insert_image(new_page.rect, stream=pix.tobytes("png"))
    new_doc.save(scanned_path)
    new_doc.close()
    doc.close()
    
    # 2. Check if the engine detects it as scanned
    print("Verifying scan detection...")
    is_scan = is_scanned_pdf(scanned_path)
    print(f"Detected as scanned: {is_scan}")
    
    # 3. Extract text (this triggers EasyOCR)
    print("Running extraction (EasyOCR fallback)...")
    text, status, reason = extract_text_from_pdf(scanned_path)
    print(f"Status: {status} | Reason: {reason}")
    print(f"Word count recovered: {len(text.split())}")
    print(f"Sample recovered text (First 200 chars):")
    print(text[:200])
    
    # Cleanup test file
    if os.path.exists(scanned_path):
        os.remove(scanned_path)

if __name__ == "__main__":
    test_ocr()
