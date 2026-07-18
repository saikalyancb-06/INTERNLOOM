def resolve_conflicts_and_confidence(candidate_data, skill_score, matched_details):
    """
    Resolve signal conflicts and couple parse quality to final score & confidence.
    Returns:
      - final_score: float (0.0 to 100.0) or None
      - confidence: 'High' | 'Medium' | 'Low'
      - reasoning_bullets: list of strings (length 3)
    """
    parse_status = candidate_data.get("parse_status", "Clean")
    
    # 1. Handle Failed Parse immediately
    if parse_status == "Failed":
        return None, "Low", [
            "Parsing failed completely due to layout, encoding, or OCR limitations.",
            "Requires immediate human review.",
            f"Error details: {candidate_data.get('parse_reason', 'Unknown error')}"
        ]
        
    cgpa = candidate_data.get("cgpa")
    projects = candidate_data.get("projects", [])
    degree = candidate_data.get("degree", "")
    branch = candidate_data.get("branch", "")
    
    # Calculate initial score based on 70% skills / 30% CGPA
    # CGPA score is normalized to percentage (CGPA / 10 * 100)
    cgpa_percentage = (cgpa / 10.0) * 100.0 if cgpa is not None else 60.0  # default to 6.0/10 if not found
    
    initial_score = (skill_score * 0.7) + (cgpa_percentage * 0.3)
    
    adjustments = 0.0
    reasoning_bullets = []
    
    # Conflict 1: High CGPA + Zero Projects
    if cgpa is not None and cgpa >= 8.5 and len(projects) == 0:
        adjustments -= 5.0
        reasoning_bullets.append("High academic performance (CGPA >= 8.5) but lacks practical projects.")
    elif len(projects) > 0:
        reasoning_bullets.append(f"Demonstrated practical exposure with {len(projects)} projects.")
        
    # Conflict 2: Low CGPA + Multiple Projects
    if cgpa is not None and cgpa < 7.0 and len(projects) >= 2:
        adjustments += 5.0  # offset penalty
        reasoning_bullets.append("Lower academic CGPA compensated by multiple strong hands-on projects.")
    elif cgpa is not None and cgpa >= 7.5:
        reasoning_bullets.append("Strong academic credentials meeting or exceeding requirements.")
        
    # Conflict 3: Perfect Skill Match + Non-CS Degree
    is_cs = False
    if branch:
        branch_lower = branch.lower()
        if "computer" in branch_lower or "information" in branch_lower or "data science" in branch_lower or "ds" == branch_lower or "cs" == branch_lower:
            is_cs = True
            
    if skill_score >= 80.0 and not is_cs:
        reasoning_bullets.append("Strong skill alignment compensating for non-Computer Science branch.")
    elif is_cs:
        reasoning_bullets.append("Relevant Computer Science academic background.")
        
    # 4. Confidence Mapping & Capping
    confidence = "High"
    if parse_status == "Partial":
        confidence = "Medium"
        reasoning_bullets.append("Confidence capped at Medium due to partial parse quality.")
        # Cap the score to a max of 70
        final_score = min(initial_score + adjustments, 70.0)
    else:
        # Check matching quality to decide confidence
        exact_matches = sum(1 for m in matched_details if m["match_type"] in ["exact", "synonym"])
        implicit_matches = sum(1 for m in matched_details if m["match_type"] == "implicit")
        
        # If too many implicit or no-match skills, lower confidence
        if implicit_matches > 2 or len(matched_details) == 0:
            confidence = "Medium"
        if candidate_data.get("grade_assumption") and "Assumed" in candidate_data.get("grade_assumption"):
            confidence = "Low"
            reasoning_bullets.append("Confidence adjusted to Low due to grade scale assumption.")
            
        final_score = min(max(initial_score + adjustments, 0.0), 100.0)
        
    # Fill in factual bullets if we have fewer than 3
    if len(reasoning_bullets) < 3:
        total_req = sum(1 for m in matched_details if m["category"] == "required")
        matched_req = sum(1 for m in matched_details if m["category"] == "required" and m["match_type"] is not None)
        bullet_req = f"{matched_req} of {total_req} required skills matched."
        if bullet_req not in reasoning_bullets and total_req > 0:
            reasoning_bullets.append(bullet_req)
            
    if len(reasoning_bullets) < 3:
        total_pref = sum(1 for m in matched_details if m["category"] == "preferred")
        matched_pref = sum(1 for m in matched_details if m["category"] == "preferred" and m["match_type"] is not None)
        bullet_pref = f"{matched_pref} of {total_pref} preferred skills matched."
        if bullet_pref not in reasoning_bullets and total_pref > 0:
            reasoning_bullets.append(bullet_pref)
            
    if len(reasoning_bullets) < 3:
        bullet_parse = f"Parsed with {parse_status} status."
        if bullet_parse not in reasoning_bullets:
            reasoning_bullets.append(bullet_parse)
            
    # Truncate to 3 bullets if we have more
    reasoning_bullets = reasoning_bullets[:3]
    
    return round(final_score, 2), confidence, reasoning_bullets
