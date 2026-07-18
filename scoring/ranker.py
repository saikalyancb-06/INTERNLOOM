def rank_candidates(candidates_results, slots, min_cgpa=0.0, cutoff_score=50.0):
    """
    Groups candidates into:
      - Shortlisted: Top-N (slots) candidates above score cutoff and meeting (or close to) CGPA requirements
      - Reserve List: Candidates above cutoff but outside the slot count limit
      - Not Shortlisted: Qualified but score below cutoff
      - Failed Parse: Parsers could not process
    """
    shortlist = []
    reserve_list = []
    failed_list = []
    unqualified_list = []
    
    # Separate failed parses first
    scored_candidates = []
    for c in candidates_results:
        if c.get("parse_status") == "Failed" or c.get("score") is None:
            failed_list.append(c)
        else:
            scored_candidates.append(c)
            
    # Sort scored candidates by score descending, then by CGPA descending
    scored_candidates.sort(key=lambda x: (x["score"], x.get("cgpa") or 0.0), reverse=True)
    
    for candidate in scored_candidates:
        cgpa = candidate.get("cgpa")
        
        # Check CGPA minimum
        if min_cgpa > 0.0:
            if cgpa is None:
                candidate["disqualification_reason"] = f"CGPA not detected (minimum {min_cgpa} required)"
                unqualified_list.append(candidate)
                continue
            elif cgpa < min_cgpa:
                candidate["disqualification_reason"] = f"Below CGPA minimum ({min_cgpa} required, candidate has {cgpa})"
                unqualified_list.append(candidate)
                continue
                
        # Check cutoff score
        if candidate["score"] >= cutoff_score:
            if len(shortlist) < slots:
                shortlist.append(candidate)
            else:
                reserve_list.append(candidate)
        else:
            unqualified_list.append(candidate)
            
    return {
        "shortlist": shortlist,
        "reserve_list": reserve_list,
        "failed_list": failed_list,
        "unqualified_list": unqualified_list
    }
