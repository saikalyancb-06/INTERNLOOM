import json
import re

def clean_skill_name(name):
    return name.lower().strip()

def match_single_skill(candidate_skills, jd_skill, synonyms_map, candidate_text=""):
    """
    Match a single target JD skill against candidate's profile.
    Returns: (match_type, multiplier)
      - match_type: 'exact', 'synonym', 'partial', 'implicit', or None
      - multiplier: float (0.0 to 1.0)
    """
    config_path = "config.json"
    try:
        with open(config_path, "r") as f:
            weights = json.load(f).get("weights", {}).get("match_types", {})
    except Exception:
        weights = {"exact": 1.0, "synonym": 1.0, "partial": 0.5, "implicit": 0.3}

    jd_clean = clean_skill_name(jd_skill)
    candidate_skills_clean = [clean_skill_name(s) for s in candidate_skills]
    
    # 1. Exact Match
    if jd_clean in candidate_skills_clean:
        return 'exact', weights.get("exact", 1.0)
        
    # 2. Synonym Match
    # Check if any synonyms of the JD skill match any candidate skills
    jd_syns = synonyms_map.get(jd_clean, [])
    for syn in jd_syns:
        if clean_skill_name(syn) in candidate_skills_clean:
            return 'synonym', weights.get("synonym", 1.0)
            
    # 3. Partial Match
    # E.g., target is "PostgreSQL", candidate has "SQL" or "Database"
    # We check if the candidate skill is a substring of JD skill, or vice-versa
    for s in candidate_skills_clean:
        if s and jd_clean and (s in jd_clean or jd_clean in s):
            # Exclude very short strings
            if len(s) > 2 and len(jd_clean) > 2:
                return 'partial', weights.get("partial", 0.5)
                
    # 4. Implicit Match
    # Look for keywords in candidate text/projects indicating implicit usage
    # E.g., REST API: "endpoint", "request", "axios", "fetch", "http", "swagger", "postman"
    implicit_keywords = {
        "rest api consumption": ["axios", "fetch", "http client", "api call", "endpoints", "consuming"],
        "rest api design": ["express", "flask", "fastapi", "endpoints", "restful", "controllers", "routes"],
        "sql or nosql db": ["queries", "schema", "table", "document", "insert", "select", "mongodb", "postgres", "mysql"],
        "git/github": ["commits", "repo", "pull request", "merge", "version control"],
        "deployment basics": ["deployed", "heroku", "vercel", "aws", "docker", "netlify", "pages"]
    }
    
    if jd_clean in implicit_keywords and candidate_text:
        text_lower = candidate_text.lower()
        matches = [kw for kw in implicit_keywords[jd_clean] if kw in text_lower]
        if len(matches) >= 2:  # at least 2 indicators
            return 'implicit', weights.get("implicit", 0.3)
            
    return None, 0.0

def score_skills(candidate_skills, required_skills, preferred_skills, synonyms_map, candidate_text="", weights_config=None):
    """
    Score skills based on required and preferred skill sets.
    """
    if not weights_config:
        weights_config = {
            "required_multiplier": 1.0,
            "preferred_multiplier": 0.4,
            "match_types": {"exact": 1.0, "synonym": 1.0, "partial": 0.5, "implicit": 0.3}
        }
        
    req_mult = weights_config.get("required_multiplier", 1.0)
    pref_mult = weights_config.get("preferred_multiplier", 0.4)
    
    total_max_points = (len(required_skills) * req_mult) + (len(preferred_skills) * pref_mult)
    if total_max_points == 0:
        return 0.0, []
        
    earned_points = 0.0
    match_details = []
    
    # Evaluate Required Skills
    for skill in required_skills:
        match_type, multiplier = match_single_skill(candidate_skills, skill, synonyms_map, candidate_text)
        points = req_mult * multiplier
        earned_points += points
        match_details.append({
            "skill": skill,
            "category": "required",
            "match_type": match_type,
            "score": round(points, 2)
        })
        
    # Evaluate Preferred Skills
    for skill in preferred_skills:
        match_type, multiplier = match_single_skill(candidate_skills, skill, synonyms_map, candidate_text)
        points = pref_mult * multiplier
        earned_points += points
        match_details.append({
            "skill": skill,
            "category": "preferred",
            "match_type": match_type,
            "score": round(points, 2)
        })
        
    percentage_score = (earned_points / total_max_points) * 100.0
    return round(percentage_score, 2), match_details
