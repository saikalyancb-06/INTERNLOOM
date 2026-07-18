import re
import json

def load_config():
    try:
        config_path = "config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"synonyms": {}, "weights": {}, "default_job_descriptions": {}}

def clean_text_for_search(text):
    return text.lower().replace("\n", " ").replace("\r", " ")

def extract_name(text):
    """
    Extract name by looking at the first 3 lines of non-empty text.
    Exclude common headings, emails, phone numbers, and addresses.
    """
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return "Unknown Candidate"
        
    for line in lines[:3]:
        # Exclude headers/labels
        if any(word in line.lower() for word in ["resume", "cv", "curriculum", "vitae", "contact", "email", "phone"]):
            continue
        # Exclude contact info
        if "@" in line or any(char.isdigit() for char in line) and len(line) < 20:
            continue
        # Must look like a name (mostly alphabetical words)
        words = line.split()
        if 2 <= len(words) <= 4 and all(w.isalpha() or "." in w for w in words):
            return line
            
    # Fallback to the first line if nothing else matched
    if lines:
        first_line = lines[0]
        if len(first_line) < 50:
            return first_line
    return "Unknown Candidate"

def extract_email(text):
    email_pattern = r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'
    match = re.search(email_pattern, text)
    return match.group(0) if match else None

def extract_phone(text):
    # Regex matching common international/domestic phone formats
    phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'
    match = re.search(phone_pattern, text)
    return match.group(0).strip() if match else None

def extract_education(text):
    """
    Extract college, degree, and branch.
    """
    college = None
    degree = None
    branch = None
    
    # College Keywords
    college_keywords = ["university", "college", "institute", "technology", "iit", "nit", "bits", "iiit", "vidyapeeth", "academy", "school of"]
    
    # Degree Keywords
    degree_patterns = [
        (r'\bB\.?\s*Tech\b', "B.Tech"),
        (r'\bM\.?\s*Tech\b', "M.Tech"),
        (r'\bB\.?\s*E\b', "B.E."),
        (r'\bM\.?\s*S\b', "M.S."),
        (r'\bB\.?\s*Sc\b', "B.Sc"),
        (r'\bM\.?\s*Sc\b', "M.Sc"),
        (r'\bB\.?\s*B\.?\s*A\b', "B.B.A"),
        (r'\bM\.?\s*B\.?\s*A\b', "M.B.A"),
        (r'\bB\.?\s*C\.?\s*A\b', "B.C.A"),
        (r'\bM\.?\s*C\.?\s*A\b', "M.C.A"),
        (r'\bBachelor\s+of\s+[A-Za-z]+', None),
        (r'\bMaster\s+of\s+[A-Za-z]+', None)
    ]
    
    # Branch Keywords
    branch_keywords = {
        "computer science": ["computer science", "cs", "cse", "c.s."],
        "information technology": ["information technology", "it", "i.t."],
        "electronics": ["electronics", "ece", "telecommunication"],
        "electrical": ["electrical", "eee"],
        "mechanical": ["mechanical", "mech"],
        "civil": ["civil"],
        "data science": ["data science", "ds"],
        "cyber security": ["cyber security", "cybersec", "information security"]
    }
    
    lines = text.split("\n")
    
    # Find College
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in college_keywords):
            # Clean and assign
            college = line.strip()
            break
            
    # Find Degree
    for pattern, deg_val in degree_patterns:
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            degree = deg_val if deg_val else match.group(0)
            break
            
    # Find Branch
    text_lower = text.lower()
    for branch_name, synonyms in branch_keywords.items():
        if any(syn in text_lower for syn in synonyms):
            branch = branch_name
            break
            
    return college, degree, branch

def extract_graduation_year(text):
    # Search for year numbers in the text
    years = re.findall(r'\b(20[0-2]\d|199\d)\b', text)
    if years:
        # Return the latest year, representing graduation
        return int(max(years))
    return None

def extract_cgpa(text):
    """
    Extract CGPA/percentage/GPA and normalise to a 10-point scale.
    Returns: (normalized_cgpa, assumption_made)
    """
    normalized_cgpa = None
    assumption = None
    
    # Look for patterns like CGPA: 8.5, CGPA of 9.2, GPA 3.6/4, 82%, etc.
    patterns = [
        # CGPA/GPA with out of
        r'(?:cgpa|gpa|grade|pointer|percentage)\s*(?:of|is|:)?\s*([0-9.]+)\s*/\s*([0-9.]+)',
        # CGPA/GPA bare numbers
        r'(?:cgpa|gpa|grade|pointer)\s*(?:of|is|:)?\s*([0-9.]+)',
        # Percentage
        r'([0-9.]+)\s*%'
    ]
    
    # 1. Search with "out of" scale first (most specific)
    match_out_of = re.search(patterns[0], text, re.IGNORECASE)
    if match_out_of:
        val = float(match_out_of.group(1))
        scale = float(match_out_of.group(2))
        if scale == 10.0:
            normalized_cgpa = val
        elif scale == 4.0:
            normalized_cgpa = val * 2.5
        elif scale == 100.0 or val > 10.0:
            normalized_cgpa = val / 9.5
        else:
            # Custom scale
            normalized_cgpa = (val / scale) * 10.0
        return min(round(normalized_cgpa, 2), 10.0), f"Detected scale of /{scale} and normalised to /10 scale."
        
    # 2. Search percentage patterns
    match_pct = re.search(patterns[2], text)
    if match_pct:
        val = float(match_pct.group(1))
        if val > 100.0:
            val = val / 10.0  # Safe handling of typos
        normalized_cgpa = val / 9.5
        return min(round(normalized_cgpa, 2), 10.0), "Detected percentage scale (divided by 9.5 to normalise to 10-point CGPA)."
        
    # 3. Search simple CGPA/GPA patterns (ambiguous)
    match_simple = re.search(patterns[1], text, re.IGNORECASE)
    if match_simple:
        val = float(match_simple.group(1))
        if val > 10.0:
            # Treat as percentage
            normalized_cgpa = val / 9.5
            assumption = "Assumed percentage scale due to value > 10 (divided by 9.5)."
        elif 4.0 < val <= 10.0:
            # Treat as 10-point scale
            normalized_cgpa = val
            assumption = "Assumed 10-point scale due to value between 4.0 and 10.0."
        else:
            # Treat as 4-point GPA
            normalized_cgpa = val * 2.5
            assumption = "Assumed 4-point scale due to value <= 4.0 (multiplied by 2.5)."
        return min(round(normalized_cgpa, 2), 10.0), assumption
        
    # 4. Fallback search: scan for numbers that might be CGPA
    # Look for things like "8.5 CGPA" or "78.2 %"
    fallback_cgpa = re.search(r'\b([0-9.]+)\s*(?:cgpa|gpa)\b', text, re.IGNORECASE)
    if fallback_cgpa:
        val = float(fallback_cgpa.group(1))
        if val > 10.0:
            normalized_cgpa = val / 9.5
            assumption = "Assumed percentage scale (divided by 9.5)."
        elif val <= 4.0:
            normalized_cgpa = val * 2.5
            assumption = "Assumed 4-point scale (multiplied by 2.5)."
        else:
            normalized_cgpa = val
            assumption = "Assumed 10-point scale."
        return min(round(normalized_cgpa, 2), 10.0), assumption
        
    return None, "No CGPA/percentage detected. Manual review required."

def extract_skills_from_text(text, synonyms_map):
    """
    Search the entire text for candidate skills using the synonyms map.
    """
    text_lower = clean_text_for_search(text)
    matched_skills = set()
    
    for main_skill, synonyms in synonyms_map.items():
        # Include the main skill as a synonym
        all_syns = set(synonyms + [main_skill])
        for syn in all_syns:
            # Use word boundaries for matching, escaping special characters
            escaped_syn = re.escape(syn)
            # Support matching special chars like .js, c++, etc.
            pattern = rf'\b{escaped_syn}\b'
            if re.search(pattern, text_lower):
                matched_skills.add(main_skill)
                break
                
    return sorted(matched_skills)

def extract_projects(text):
    """
    Identify project sections and pull out project title + one-line description.
    """
    projects = []
    # Try finding sections labeled Projects
    lines = text.split("\n")
    in_projects = False
    current_project = None
    
    project_headers = ["projects", "academic projects", "personal projects", "key projects"]
    other_headers = ["experience", "education", "skills", "certifications", "interests", "activities", "languages", "summary"]
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
            
        line_lower = line_strip.lower()
        
        # Check if project section begins
        if any(line_lower.startswith(h) or line_lower == h for h in project_headers):
            in_projects = True
            continue
            
        # Check if project section ends (transitions to another section)
        if in_projects and any(line_lower.startswith(h) or line_lower == h for h in other_headers):
            in_projects = False
            break
            
        if in_projects:
            # Check if this line looks like a project title (short, bullet point, capitalized)
            # E.g. "Smart Attendance System - IoT based" or "* Resume shortlisting engine"
            if len(line_strip) < 60 and (line_strip.startswith(("-", "*", "•", "1.", "2.", "3.", "4.", "5.")) or line_strip[0].isupper()):
                if current_project:
                    projects.append(current_project)
                # Clean title
                title = re.sub(r'^[-*•\d.\s]+', '', line_strip).strip()
                current_project = {"title": title, "description": ""}
            elif current_project:
                # Add line to description
                desc_line = line_strip.strip()
                if current_project["description"]:
                    current_project["description"] += " " + desc_line
                else:
                    current_project["description"] = desc_line
                    
    if current_project:
        projects.append(current_project)
        
    # Cap description to one line
    for p in projects:
        desc = p["description"]
        if len(desc) > 150:
            p["description"] = desc[:147] + "..."
        if not p["description"]:
            p["description"] = "No description provided."
            
    return projects

def extract_experience(text):
    """
    Extract work experience / internships: company, role, duration.
    """
    experience = []
    lines = text.split("\n")
    in_exp = False
    current_job = None
    
    exp_headers = ["experience", "work experience", "professional experience", "internships", "employment history"]
    other_headers = ["projects", "education", "skills", "certifications", "interests", "activities", "summary"]
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
            
        line_lower = line_strip.lower()
        
        if any(line_lower.startswith(h) or line_lower == h for h in exp_headers):
            in_exp = True
            continue
            
        if in_exp and any(line_lower.startswith(h) or line_lower == h for h in other_headers):
            in_exp = False
            break
            
        if in_exp:
            # Look for duration patterns (e.g. June 2023 - Present, 2021-2022, 6 months)
            duration_match = re.search(r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|present|20\d\d)\b', line_lower)
            if duration_match and len(line_strip) < 100:
                if current_job:
                    experience.append(current_job)
                if "|" in line_strip:
                    parts = [p.strip() for p in line_strip.split("|")]
                elif "-" in line_strip:
                    parts = [p.strip() for p in line_strip.split("-")]
                else:
                    parts = [p.strip() for p in line_strip.split(",")]
                company = parts[0] if len(parts) > 0 else "Unknown Company"
                role = parts[1] if len(parts) > 1 else "Intern"
                duration = parts[-1] if len(parts) > 2 else line_strip
                current_job = {"company": company, "role": role, "duration": duration}
            elif current_job:
                # Add details
                pass
                
    if current_job:
        experience.append(current_job)
        
    return experience

def extract_certifications(text):
    """
    Extract certifications/courses.
    """
    certs = []
    lines = text.split("\n")
    in_certs = False
    
    cert_headers = ["certifications", "courses", "achievements", "awards", "training"]
    other_headers = ["experience", "education", "skills", "projects", "summary", "languages"]
    
    for line in lines:
        line_strip = line.strip()
        if not line_strip:
            continue
            
        line_lower = line_strip.lower()
        
        if any(line_lower.startswith(h) or line_lower == h for h in cert_headers):
            in_certs = True
            continue
            
        if in_certs and any(line_lower.startswith(h) or line_lower == h for h in other_headers):
            in_certs = False
            break
            
        if in_certs:
            if line_strip.startswith(("-", "*", "•", "1.", "2.", "3.", "4.", "5.")) or len(line_strip) < 100:
                cert = re.sub(r'^[-*•\d.\s]+', '', line_strip).strip()
                if cert:
                    certs.append(cert)
                    
    return certs

def extract_candidate_data(text, parse_status, reason):
    """
    Constructs a structured Candidate object with parsed info.
    """
    if parse_status == "Failed":
        return {
            "name": "Unknown Candidate",
            "email": None,
            "phone": None,
            "college": None,
            "degree": None,
            "branch": None,
            "graduation_year": None,
            "cgpa": None,
            "grade_assumption": "Failed Parse",
            "skills": [],
            "projects": [],
            "experience": [],
            "certifications": [],
            "parse_status": "Failed",
            "parse_reason": reason
        }
        
    config = load_config()
    synonyms_map = config.get("synonyms", {})
    
    name = extract_name(text)
    email = extract_email(text)
    phone = extract_phone(text)
    college, degree, branch = extract_education(text)
    grad_year = extract_graduation_year(text)
    cgpa, assumption = extract_cgpa(text)
    skills = extract_skills_from_text(text, synonyms_map)
    projects = extract_projects(text)
    experience = extract_experience(text)
    certs = extract_certifications(text)
    
    return {
        "name": name,
        "email": email,
        "phone": phone,
        "college": college,
        "degree": degree,
        "branch": branch,
        "graduation_year": grad_year,
        "cgpa": cgpa,
        "grade_assumption": assumption,
        "skills": skills,
        "projects": projects,
        "experience": experience,
        "certifications": certs,
        "parse_status": parse_status,
        "parse_reason": reason
    }
