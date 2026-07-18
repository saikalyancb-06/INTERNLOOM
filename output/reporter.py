import json
import os

def generate_markdown_report(jd_name, jd_info, results, cutoff_score, duplicates_removed=0, missing_skill_gap="", warning_unreliable=False):
    """
    Generate a human-readable Markdown report for a specific Job Description.
    """
    shortlist = results["shortlist"]
    reserve = results["reserve_list"]
    failed = results["failed_list"]
    unqualified = results["unqualified_list"]
    
    total_evaluated = len(shortlist) + len(reserve) + len(failed) + len(unqualified)
    
    md = []
    md.append(f"# InternLoom Shortlist Report: {jd_info.get('role', jd_name)}")
    md.append("")
    md.append("## Executive Summary")
    md.append(f"- **Candidates Evaluated**: {total_evaluated}")
    md.append(f"- **Candidates Shortlisted**: {len(shortlist)} (Slots: {jd_info.get('slots', 'N/A')})")
    md.append(f"- **Reserve List Count**: {len(reserve)}")
    md.append(f"- **Parse Failures**: {len(failed)}")
    md.append(f"- **Duplicates Removed**: {duplicates_removed}")
    if missing_skill_gap:
        md.append(f"- **Commonly Missing Required Skill**: {missing_skill_gap}")
    if warning_unreliable:
        md.append("- **Warning**: No explicit skills detected in JD — scoring may be unreliable.")
    md.append(f"- **Score Cutoff Used**: {cutoff_score}/100")
    md.append("- **Scoring Formula**: 70% skill match + 30% normalized CGPA, adjusted for signal conflicts (see design_decisions.md)")
    md.append("")
    
    # 1. Ranked Shortlist
    md.append("## Ranked Shortlist")
    if not shortlist:
        md.append("*No candidates qualified for the shortlist.*")
    else:
        md.append("| Rank | Candidate Name | Score | Confidence | Parse Quality | Top Match Reasoning |")
        md.append("|---|---|---|---|---|---|")
        for i, c in enumerate(shortlist, 1):
            bullets = "<br>".join([f"• {b}" for b in c['reasoning']])
            md.append(f"| {i} | {c['name']} | {c['score']}/100 | {c['confidence']} | {c['parse_status']} | {bullets} |")
    md.append("")
    
    # 2. Reserve List
    md.append("## Reserve List")
    if not reserve:
        md.append("*No candidates in the reserve list.*")
    else:
        md.append("| Rank | Candidate Name | Score | Confidence | Parse Quality | Points Below Shortlist | Key Notes |")
        md.append("|---|---|---|---|---|---|---|")
        for i, c in enumerate(reserve, 1):
            bullets = "<br>".join([f"• {b}" for b in c['reasoning']])
            pts_below = f"{c.get('points_below_shortlist', 0.0)} pts below shortlist"
            md.append(f"| {i} | {c['name']} | {c['score']}/100 | {c['confidence']} | {c['parse_status']} | {pts_below} | {bullets} |")
    md.append("")
    
    # 3. Failed Parse List (No scores)
    md.append("## Failed Parse & Review Queue")
    if not failed:
        md.append("*No parsing failures encountered.*")
    else:
        md.append("| Filename | Status | Failure Reason | Recommendation |")
        md.append("|---|---|---|---|")
        for c in failed:
            md.append(f"| {c.get('filename', 'Unknown')} | {c['parse_status']} | {c.get('parse_reason', 'N/A')} | **Requires manual human review** |")
    md.append("")
    
    return "\n".join(md)

def save_outputs(jd_name, results, output_dir):
    """
    Save JSON and Markdown outputs.
    """
    os.makedirs(output_dir, exist_ok=True)
    
    # Save JSON
    json_path = os.path.join(output_dir, f"{jd_name}_results.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
        
    return json_path

def generate_parse_quality_report(all_resumes_data):
    """
    Generates the parse_quality_report.md content.
    """
    md = []
    md.append("# Parse Quality Report")
    md.append("")
    md.append("| Filename | Parse Status | Details / Reason |")
    md.append("|---|---|---|")
    
    for filename, data in sorted(all_resumes_data.items()):
        status = data.get("parse_status", "Clean")
        reason = data.get("parse_reason", "Parsed cleanly")
        md.append(f"| {filename} | {status} | {reason} |")
        
    return "\n".join(md)
