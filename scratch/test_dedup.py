import sys
import os
import re

# Add root folder to path so we can import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scoring.ranker import rank_candidates

def get_dedup_key(cand):
    email = cand.get("email")
    if email and isinstance(email, str) and email.strip():
        return ("email", email.strip().lower())
    
    name = cand.get("name") or ""
    college = cand.get("college") or ""
    
    is_unknown_name = not name or name.strip().lower() == "unknown candidate"
    is_empty_college = not college or not college.strip()
    
    if cand.get("parse_status") == "Partial" and is_unknown_name and is_empty_college:
        return ("filename", cand.get("filename", ""))
        
    norm_name = re.sub(r'[^a-z0-9]', '', name.strip().lower())
    norm_college = re.sub(r'[^a-z0-9]', '', college.strip().lower())
    return ("name_college", f"{norm_name}_{norm_college}")

def run_deduplication(evaluated_candidates):
    deduplicated_candidates = []
    candidates_to_group = []
    
    for cand in evaluated_candidates:
        if cand.get("parse_status") == "Failed":
            deduplicated_candidates.append(cand)
        else:
            candidates_to_group.append(cand)
            
    from collections import defaultdict
    groups = defaultdict(list)
    for cand in candidates_to_group:
        key = get_dedup_key(cand)
        groups[key].append(cand)
        
    duplicates_removed_count = 0
    parse_quality_data = {}
    for key, cand_list in groups.items():
        if len(cand_list) == 1:
            deduplicated_candidates.append(cand_list[0])
            continue
            
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
        
        kept_filename = kept_candidate["filename"]
        for dropped_candidate in cand_list[:-1]:
            dropped_filename = dropped_candidate["filename"]
            parse_quality_data[dropped_filename] = {
                "parse_status": dropped_candidate.get("parse_status", "Clean"),
                "parse_reason": f"Identified as duplicate of {kept_filename} and excluded from ranking."
            }
            
    return deduplicated_candidates, duplicates_removed_count, parse_quality_data

def test_deduplication_scenarios():
    print("Running deduplication logic unit tests...")
    
    # 1. Test case: Duplicate email groupings (keep highest score candidate)
    candidates = [
        {"filename": "dup1.pdf", "email": "test@gmail.com", "name": "Test User", "college": "BMS", "score": 85.0, "parse_status": "Clean"},
        {"filename": "dup2.pdf", "email": "TEST@gmail.com", "name": "Test User 2", "college": "BMS College", "score": 90.0, "parse_status": "Clean"},
        {"filename": "dup3.pdf", "email": "test@gmail.com", "name": "Test User 3", "college": "BMS", "score": 70.0, "parse_status": "Partial"}
    ]
    deduped, removed_count, pq = run_deduplication(candidates)
    assert len(deduped) == 1, f"Expected 1 candidate, got {len(deduped)}"
    assert deduped[0]["filename"] == "dup2.pdf", f"Expected dup2.pdf to be kept, got {deduped[0]['filename']}"
    assert removed_count == 2, f"Expected removed count 2, got {removed_count}"
    assert "dup1.pdf" in pq
    assert "dup3.pdf" in pq
    print("  -> Duplicate email grouping test: PASS")
    
    # 2. Test case: Skip Failed parses entirely
    candidates = [
        {"filename": "failed1.pdf", "email": None, "name": None, "college": None, "score": None, "parse_status": "Failed"},
        {"filename": "failed2.pdf", "email": None, "name": None, "college": None, "score": None, "parse_status": "Failed"}
    ]
    deduped, removed_count, pq = run_deduplication(candidates)
    assert len(deduped) == 2, f"Expected 2 candidates, got {len(deduped)}"
    assert removed_count == 0, f"Expected 0 removed, got {removed_count}"
    print("  -> Failed parse bypass test: PASS")
    
    # 3. Test case: Low-signal Partial parses bypass name/college grouping (using filename instead)
    candidates = [
        {"filename": "partial1.pdf", "email": None, "name": "Unknown Candidate", "college": "", "score": 40.0, "parse_status": "Partial"},
        {"filename": "partial2.pdf", "email": None, "name": "", "college": None, "score": 42.0, "parse_status": "Partial"}
    ]
    deduped, removed_count, pq = run_deduplication(candidates)
    assert len(deduped) == 2, f"Expected 2 candidates, got {len(deduped)}"
    assert removed_count == 0, f"Expected 0 removed, got {removed_count}"
    print("  -> Low-signal Partial parse bypass test: PASS")
    
    print("\nAll deduplication unit tests passed successfully!")

if __name__ == "__main__":
    test_deduplication_scenarios()
