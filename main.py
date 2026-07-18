import os
import argparse
import json
import re
try:
    from parsing.pdf_parser import extract_text_from_pdf
    from parsing.docx_parser import extract_text_from_docx
    from parsing.extractor import extract_candidate_data, load_config
    from scoring.matcher import score_skills
    from scoring.rules import resolve_conflicts_and_confidence
    from scoring.ranker import rank_candidates
    from output.reporter import generate_markdown_report, save_outputs, generate_parse_quality_report
except ModuleNotFoundError as e:
    print(f"\n[ERROR] Missing dependency: {e}")
    print("Please make sure you have activated your virtual environment or installed dependencies using:")
    print("    pip install -r requirements.txt\n")
    import sys
    sys.exit(1)
def extract_text_from_txt(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            text = f.read()
        return text, "Clean", "Parsed successfully"
    except Exception as e:
        return "", "Failed", f"Text file read error: {str(e)}"

def extract_text_from_xml(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            xml_content = f.read()
        text = re.sub(r'<[^>]+>', ' ', xml_content)
        text = re.sub(r'\s+', ' ', text).strip()
        return text, "Clean", "Parsed successfully"
    except Exception as e:
        return "", "Failed", f"XML parse error: {str(e)}"

def parse_unstructured_jd(jd_text, config_synonyms):
    """
    Parses a plain English unstructured JD and returns structured JD dict.
    """
    role = "Custom Role"
    # Find role title from first line if short
    lines = [l.strip() for l in jd_text.split("\n") if l.strip()]
    if lines and len(lines[0]) < 50:
        role = lines[0]
        
    jd_lower = jd_text.lower()
    
    # 1. Search CGPA min
    min_cgpa = 6.0
    cgpa_match = re.search(r'(?:cgpa|gpa|percentage|pointer)\b\s*(?:min|minimum|of)?\s*(?:is|:)?\s*([0-9.]+)', jd_lower)
    if cgpa_match:
        try:
            val = float(cgpa_match.group(1))
            if val > 10.0: # percentage
                min_cgpa = round(val / 9.5, 2)
            elif val <= 4.0: # GPA
                min_cgpa = val * 2.5
            else:
                min_cgpa = val
        except ValueError:
            pass
            
    # 2. Extract skills mentioned in the JD text
    found_skills = []
    for main_skill, synonyms in config_synonyms.items():
        all_syns = synonyms + [main_skill]
        for syn in all_syns:
            escaped_syn = re.escape(syn)
            if re.search(rf'\b{escaped_syn}\b', jd_lower):
                found_skills.append(main_skill)
                break
                
    # Separate into required vs preferred
    # Look for divider headers like "preferred", "plus", "nice to have", "bonus"
    preferred_indicators = ["preferred", "plus", "nice to have", "bonus", "desirable", "good to have"]
    preferred_idx = len(jd_lower)
    for ind in preferred_indicators:
        idx = jd_lower.find(ind)
        if idx != -1 and idx < preferred_idx:
            preferred_idx = idx
            
    required_skills = []
    preferred_skills = []
    
    # Re-evaluate based on index position in the JD text
    for skill in found_skills:
        # Find skill position
        pos = jd_lower.find(skill)
        if pos != -1 and pos >= preferred_idx:
            preferred_skills.append(skill)
        else:
            required_skills.append(skill)
            
    # Default to required if no preferred
    if not preferred_skills and required_skills:
        # Move last 30% of skills to preferred as a heuristic
        split_point = int(len(required_skills) * 0.7)
        preferred_skills = required_skills[split_point:]
        required_skills = required_skills[:split_point]
        
    warning_unreliable = False
    if not required_skills and not preferred_skills:
        config = load_config()
        default_jds = config.get("default_job_descriptions", {})
        
        inferred_key = None
        search_target = (role + " " + jd_text).lower()
        if "frontend" in search_target:
            inferred_key = "frontend_developer"
        elif "backend" in search_target:
            inferred_key = "backend_developer"
        elif "full stack" in search_target or "fullstack" in search_target:
            inferred_key = "full_stack_developer"
        elif "database" in search_target or "db" in search_target or "sql" in search_target:
            inferred_key = "database_developer"
        elif "api" in search_target or "integration" in search_target:
            inferred_key = "api_integration_developer"
            
        if inferred_key and inferred_key in default_jds:
            defaults = default_jds[inferred_key]
            required_skills = defaults.get("required_skills", [])
            preferred_skills = defaults.get("preferred_skills", [])
            min_cgpa = defaults.get("min_cgpa", min_cgpa)
            role = defaults.get("role", role)
        else:
            required_skills = ["general"]
            preferred_skills = []
            warning_unreliable = True
            
    return {
        "role": role,
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "min_cgpa": min_cgpa,
        "slots": 5,
        "warning_unreliable": warning_unreliable
    }

def main():
    parser = argparse.ArgumentParser(description="InternLoom Resume Shortlisting Engine")
    parser.add_argument("--input", required=True, help="Path to folder of resumes")
    parser.add_argument("--jd", required=True, help="Role name (from config) OR path to a JD file OR raw JD text")
    parser.add_argument("--output", default="output_results", help="Directory path to save outputs")
    parser.add_argument("--cutoff", type=float, default=50.0, help="Cutoff score for shortlisting (default: 50.0)")
    
    args = parser.parse_args()
    
    config = load_config()
    synonyms_map = config.get("synonyms", {})
    weights_config = config.get("weights", {})
    
    # 1. Resolve Job Description
    jd_info = None
    jd_name = args.jd
    
    # Check if jd matches default role names
    default_jds = config.get("default_job_descriptions", {})
    if args.jd in default_jds:
        jd_info = default_jds[args.jd]
    elif os.path.exists(args.jd):
        # Could be a JSON JD or txt JD
        with open(args.jd, "r", encoding="utf-8") as f:
            content = f.read().strip()
        if args.jd.endswith(".json"):
            try:
                jd_info = json.loads(content)
                jd_name = os.path.basename(args.jd).replace(".json", "")
            except Exception as e:
                print(f"Error parsing JSON JD file: {e}. Treating as plain text.")
                jd_info = parse_unstructured_jd(content, synonyms_map)
        else:
            jd_info = parse_unstructured_jd(content, synonyms_map)
            jd_name = os.path.basename(args.jd).replace(".txt", "")
    else:
        # Treat as raw pasted plain English text
        jd_info = parse_unstructured_jd(args.jd, synonyms_map)
        jd_name = "custom_role"
        
    print(f"Loaded Job Description: {jd_info.get('role', 'Custom')}")
    print(f"Required Skills: {jd_info.get('required_skills')}")
    print(f"Preferred Skills: {jd_info.get('preferred_skills')}")
    print(f"Min CGPA Requirement: {jd_info.get('min_cgpa')}")
    print(f"Available Slots: {jd_info.get('slots')}")
    print("-" * 50)
    
    # 2. Process all resumes in the folder
    resumes_dir = args.input
    if not os.path.isdir(resumes_dir):
        print(f"Error: input directory '{resumes_dir}' does not exist.")
        return
        
    # Process resume formats (.pdf, .docx, .doc, .txt, .xml)
    allowed_exts = ('.pdf', '.docx', '.doc', '.txt', '.xml')
    resume_files = [f for f in os.listdir(resumes_dir) if os.path.isfile(os.path.join(resumes_dir, f)) and f.lower().endswith(allowed_exts)]
    
    if not resume_files:
        print(f"No resume files (.pdf, .docx, .doc, .txt, .xml) found in directory: {resumes_dir}")
        return
        
    print(f"Found {len(resume_files)} resumes. Commencing Stage 1 (Extraction)...")
    
    all_extracted_candidates = []
    parse_quality_data = {}
    
    for filename in resume_files:
        file_path = os.path.join(resumes_dir, filename)
        print(f"Parsing: {filename}...")
        
        text = ""
        parse_status = "Clean"
        reason = "Parsed successfully"
        ext = os.path.splitext(filename)[1].lower()
        
        if ext == '.pdf':
            text, parse_status, reason = extract_text_from_pdf(file_path)
        elif ext == '.docx':
            text, parse_status, reason = extract_text_from_docx(file_path)
        elif ext == '.txt':
            text, parse_status, reason = extract_text_from_txt(file_path)
        elif ext == '.xml':
            text, parse_status, reason = extract_text_from_xml(file_path)
        elif ext == '.doc':
            parse_status = "Failed"
            reason = "Unsupported legacy format: .doc. Please convert to PDF or DOCX."
            
        candidate_obj = extract_candidate_data(text, parse_status, reason)
        candidate_obj["filename"] = filename
        candidate_obj["raw_text"] = text
        
        all_extracted_candidates.append(candidate_obj)
        parse_quality_data[filename] = {
            "parse_status": parse_status,
            "parse_reason": reason
        }
        
    print("-" * 50)
    print("Stage 1 complete. Commencing Stage 2 (Matching & Scoring)...")
    
    evaluated_candidates = []
    
    for cand in all_extracted_candidates:
        if cand["parse_status"] == "Failed":
            # Failed parses have score null and go straight to failed list
            cand["score"] = None
            cand["confidence"] = "Low"
            cand["reasoning"] = [
                "Parsing failed completely. File could not be processed.",
                "Requires manual review.",
                f"Error details: {cand['parse_reason']}"
            ]
            evaluated_candidates.append(cand)
            continue
            
        # Match skills
        skill_score, matched_details = score_skills(
            candidate_skills=cand["skills"],
            required_skills=jd_info.get("required_skills", []),
            preferred_skills=jd_info.get("preferred_skills", []),
            synonyms_map=synonyms_map,
            candidate_text=cand["raw_text"],
            weights_config=weights_config
        )
        
        # Resolve conflicts and confidence
        final_score, confidence, reasoning = resolve_conflicts_and_confidence(
            candidate_data=cand,
            skill_score=skill_score,
            matched_details=matched_details
        )
        
        if jd_info.get("warning_unreliable"):
            confidence = "Low"
            # Append warning if not already in reasoning
            warning_msg = "No explicit skills detected in JD — scoring may be unreliable."
            if warning_msg not in reasoning:
                reasoning.append(warning_msg)
        
        cand["score"] = final_score
        cand["confidence"] = confidence
        cand["reasoning"] = reasoning
        cand["matched_skills_breakdown"] = matched_details
        
        evaluated_candidates.append(cand)
        
    # 2.5. Perform deduplication of candidates
    deduplicated_candidates = []
    candidates_to_group = []
    
    # Process Failed parses immediately (no grouping)
    for cand in evaluated_candidates:
        if cand.get("parse_status") == "Failed":
            deduplicated_candidates.append(cand)
        else:
            candidates_to_group.append(cand)
            
    # Helper to generate unique deduplication key
    def get_dedup_key(cand):
        email = cand.get("email")
        if email and isinstance(email, str) and email.strip():
            return ("email", email.strip().lower())
        
        name = cand.get("name") or ""
        college = cand.get("college") or ""
        
        # Handing low-signal partial parses
        is_unknown_name = not name or name.strip().lower() == "unknown candidate"
        is_empty_college = not college or not college.strip()
        
        if cand.get("parse_status") == "Partial" and is_unknown_name and is_empty_college:
            return ("filename", cand.get("filename", ""))
            
        norm_name = re.sub(r'[^a-z0-9]', '', name.strip().lower())
        norm_college = re.sub(r'[^a-z0-9]', '', college.strip().lower())
        return ("name_college", f"{norm_name}_{norm_college}")
        
    from collections import defaultdict
    groups = defaultdict(list)
    for cand in candidates_to_group:
        key = get_dedup_key(cand)
        groups[key].append(cand)
        
    duplicates_removed_count = 0
    for key, cand_list in groups.items():
        if len(cand_list) == 1:
            deduplicated_candidates.append(cand_list[0])
            continue
            
        # Determine the best candidate to keep
        def sort_key(c):
            score = c.get("score") if c.get("score") is not None else -1.0
            status_val = 0
            status = c.get("parse_status", "Clean")
            if status == "Clean":
                status_val = 2
            elif status == "Partial":
                status_val = 1
            return (score, status_val, c.get("filename", ""))
            
        cand_list.sort(key=sort_key)
        kept_candidate = cand_list[-1]
        deduplicated_candidates.append(kept_candidate)
        duplicates_removed_count += len(cand_list) - 1
        
        # Log dropped duplicates in the parse quality report
        kept_filename = kept_candidate["filename"]
        for dropped_candidate in cand_list[:-1]:
            dropped_filename = dropped_candidate["filename"]
            original_reason = parse_quality_data.get(dropped_filename, {}).get("parse_reason", "Parsed successfully")
            parse_quality_data[dropped_filename] = {
                "parse_status": dropped_candidate.get("parse_status", "Clean"),
                "parse_reason": f"Identified as duplicate of {kept_filename} and excluded from ranking. (Original: {original_reason})"
            }

    # 3. Perform slot-aware ranking
    ranking_results = rank_candidates(
        candidates_results=deduplicated_candidates,
        slots=jd_info.get("slots", 5),
        min_cgpa=jd_info.get("min_cgpa", 0.0),
        cutoff_score=args.cutoff
    )
    
    # Remove raw text from output JSON to keep file sizes clean
    clean_results = {}
    for group, list_cand in ranking_results.items():
        clean_list = []
        for c in list_cand:
            c_copy = c.copy()
            c_copy.pop("raw_text", None)
            clean_list.append(c_copy)
        clean_results[group] = clean_list
        
    # Calculate commonly missing required skills across deduplicated scored candidates
    from collections import Counter
    missing_required_counts = Counter()
    scored_count = 0
    for cand in deduplicated_candidates:
        if cand.get("score") is None or cand.get("parse_status") == "Failed":
            continue
        scored_count += 1
        for md in cand.get("matched_skills_breakdown", []):
            if md.get("category") == "required" and md.get("match_type") is None:
                missing_required_counts[md["skill"]] += 1
                
    missing_skill_gap = ""
    if scored_count > 0 and missing_required_counts:
        top_skill, count = missing_required_counts.most_common(1)[0]
        pct = round((count / scored_count) * 100.0, 1)
        missing_skill_gap = f"{top_skill} (missing in {pct}%)"
        
    # 4. Save results and reports
    os.makedirs(args.output, exist_ok=True)
    
    json_path = save_outputs(jd_name, clean_results, args.output)
    md_content = generate_markdown_report(jd_name, jd_info, clean_results, args.cutoff, 
                                          duplicates_removed=duplicates_removed_count,
                                          missing_skill_gap=missing_skill_gap,
                                          warning_unreliable=jd_info.get("warning_unreliable", False))
    
    md_path = os.path.join(args.output, f"{jd_name}_results.md")
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    # Generate parse quality report
    pq_content = generate_parse_quality_report(parse_quality_data)
    pq_path = os.path.join(args.output, "parse_quality_report.md")
    with open(pq_path, "w", encoding="utf-8") as f:
        f.write(pq_content)
        
    print(f"\nProcessing Complete!")
    print(f"Results JSON: {json_path}")
    print(f"Results Markdown: {md_path}")
    print(f"Parse Quality Report: {pq_path}")
    print("-" * 50)
    print(f"Shortlisted Candidates Count: {len(ranking_results['shortlist'])}")
    print(f"Reserve List Count: {len(ranking_results['reserve_list'])}")
    print(f"Failed Parse Count: {len(ranking_results['failed_list'])}")

if __name__ == "__main__":
    main()
