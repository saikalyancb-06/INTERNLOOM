import os
import sys
import shutil

sys.path.append(os.path.abspath("."))
from parsing.pdf_parser import extract_text_from_pdf

def test_crash():
    print("=== Crash Resilience Verification Test ===")
    test_dir = "test_resumes_folder"
    os.makedirs(test_dir, exist_ok=True)
    
    # 1. Create a 0-byte PDF file
    corrupt_pdf = os.path.join(test_dir, "0_byte_corrupt.pdf")
    with open(corrupt_pdf, "wb") as f:
        pass
        
    # 2. Copy a valid PDF file
    valid_pdf_src = "resumes/web_dev__aditya_kulkarni.pdf"
    valid_pdf_dest = os.path.join(test_dir, "valid_aditya.pdf")
    shutil.copy(valid_pdf_src, valid_pdf_dest)
    
    print("Running parser on corrupt PDF (0-byte)...")
    text, status, reason = extract_text_from_pdf(corrupt_pdf)
    print(f"File: 0_byte_corrupt.pdf | Status: {status} | Reason: {reason}")
    
    print("Running parser on valid PDF...")
    text_v, status_v, reason_v = extract_text_from_pdf(valid_pdf_dest)
    print(f"File: valid_aditya.pdf | Status: {status_v} | Reason: {reason_v} | Word Count: {len(text_v.split())}")
    
    # Cleanup
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)

if __name__ == "__main__":
    test_crash()
