import os
import sys
import argparse
import json

# Add parent path to import correctly
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parsing.pdf_parser import extract_text_from_pdf
from parsing.docx_parser import extract_text_from_docx
from main import extract_text_from_txt, extract_text_from_xml
from parsing.extractor import extract_candidate_data, load_config
from scoring.matcher import score_skills
from scoring.rules import resolve_conflicts_and_confidence

def get_jd_details(jd_input):
    """
    Resolves job description input (key name, text file path, or raw text).
    """
    # 1. Check if it matches a default JD key in config
    config = load_config()
    default_jds = config.get("default_job_descriptions", {})
    if jd_input in default_jds:
        return jd_input, default_jds[jd_input]
        
    from main import parse_unstructured_jd
    synonyms_map = config.get("synonyms", {})
    
    # 2. Check if it is a path to a file
    if os.path.exists(jd_input):
        try:
            with open(jd_input, 'r', encoding='utf-8') as f:
                content = f.read().strip()
            # Try parsing as JSON first
            try:
                data = json.loads(content)
                if isinstance(data, dict):
                    return os.path.basename(jd_input), data
            except json.JSONDecodeError:
                pass
            # Fallback to plain text
            return os.path.basename(jd_input), parse_unstructured_jd(content, synonyms_map)
        except Exception as e:
            print(f"Error reading file {jd_input}: {e}")
            sys.exit(1)
            
    # 3. Handle raw text
    return "Custom Input", parse_unstructured_jd(jd_input, synonyms_map)

def main():
    parser = argparse.ArgumentParser(description="Judge Mode: Evaluate a single resume against a Job Description.")
    parser.add_argument("file", help="Path to the resume file (.pdf, .docx, .txt, .xml)")
    parser.add_argument("--jd", required=True, help="JD key, text file path, or raw comma-separated required skills")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.file):
        print(f"[ERROR] File not found: {args.file}")
        sys.exit(1)
        
    ext = os.path.splitext(args.file)[1].lower()
    if ext not in ['.pdf', '.docx', '.txt', '.xml']:
        print(f"[ERROR] Unsupported file extension: {ext}. Must be .pdf, .docx, .txt, or .xml")
        sys.exit(1)
        
    # 1. Parse File
    print(f"Analyzing {os.path.basename(args.file)}...")
    if ext == '.pdf':
        text, parse_status, reason = extract_text_from_pdf(args.file)
    elif ext == '.docx':
        text, parse_status, reason = extract_text_from_docx(args.file)
    elif ext == '.txt':
        text, parse_status, reason = extract_text_from_txt(args.file)
    elif ext == '.xml':
        text, parse_status, reason = extract_text_from_xml(args.file)
        
    # 2. Extract Data
    candidate_obj = extract_candidate_data(text, parse_status, reason)
    candidate_obj["filename"] = os.path.basename(args.file)
    candidate_obj["raw_text"] = text
    
    if parse_status == "Failed":
        print("\n" + "="*50)
        print("SINGLE CANDIDATE REPORT (JUDGE MODE)")
        print("="*50)
        print(f"Candidate Name : {candidate_obj.get('name') or 'N/A'}")
        print(f"File Name      : {candidate_obj['filename']}")
        print(f"Parse Status   : FAILED")
        print(f"Failure Reason : {reason}")
        print("="*50)
        sys.exit(0)
        
    # 3. Resolve JD
    jd_name, jd_info = get_jd_details(args.jd)
    
    # Load synonyms & weights configs
    config = load_config()
    synonyms_map = config.get("synonyms", {})
    weights_config = config.get("weights", {})
    
    # 4. Score
    skill_score, matched_details = score_skills(
        candidate_skills=candidate_obj["skills"],
        required_skills=jd_info.get("required_skills", []),
        preferred_skills=jd_info.get("preferred_skills", []),
        synonyms_map=synonyms_map,
        candidate_text=candidate_obj["raw_text"],
        weights_config=weights_config
    )
    final_score, confidence, reasoning = resolve_conflicts_and_confidence(
        candidate_data=candidate_obj,
        skill_score=skill_score,
        matched_details=matched_details
    )
    
    if jd_info.get("warning_unreliable"):
        confidence = "Low"
        warning_msg = "No explicit skills detected in JD — scoring may be unreliable."
        if warning_msg not in reasoning:
            reasoning.append(warning_msg)
            
    # 5. Output Report to Terminal
    print("\n" + "="*60)
    print("SINGLE CANDIDATE EVALUATION REPORT (JUDGE MODE)")
    print("="*60)
    print(f"Candidate Name  : {candidate_obj.get('name') or 'Unknown Candidate'}")
    print(f"Filename        : {candidate_obj['filename']}")
    print(f"Target JD       : {jd_info.get('role', jd_name)}")
    print(f"Parse Quality   : {parse_status} ({reason})")
    print(f"Normalized CGPA : {candidate_obj.get('cgpa') or 'N/A'}")
    print(f"Email / Phone   : {candidate_obj.get('email') or 'N/A'} / {candidate_obj.get('phone') or 'N/A'}")
    print("-" * 60)
    print(f"MATCHING SCORE  : {final_score}/100")
    print(f"CONFIDENCE LEVEL: {confidence}")
    print("-" * 60)
    print("Top Match Reasoning:")
    for bullet in reasoning:
        print(f"  • {bullet}")
    print("="*60 + "\n")

if __name__ == "__main__":
    main()
