import os
import sys

sys.path.append(os.path.abspath("."))
from scoring.ranker import rank_candidates

def test_cgpa_enforcement():
    print("=== Testing CGPA Enforcement ===")
    
    # 1. Create a dummy candidate list
    # Candidate A: Strong skill score but very low CGPA
    # Candidate B: Strong skill score and high CGPA
    # Candidate C: Weak skill score but high CGPA
    candidates = [
        {
            "name": "Candidate A (Low CGPA)",
            "score": 95.0,
            "cgpa": 5.2,
            "parse_status": "Clean",
            "email": "cand_a@gmail.com"
        },
        {
            "name": "Candidate B (High CGPA)",
            "score": 90.0,
            "cgpa": 8.5,
            "parse_status": "Clean",
            "email": "cand_b@gmail.com"
        },
        {
            "name": "Candidate C (Low Skill)",
            "score": 45.0,
            "cgpa": 9.0,
            "parse_status": "Clean",
            "email": "cand_c@gmail.com"
        }
    ]
    
    # Run ranker with slots=2, min_cgpa=6.0, cutoff_score=50.0
    results = rank_candidates(candidates, slots=2, min_cgpa=6.0, cutoff_score=50.0)
    
    print("Shortlist candidates:")
    for c in results["shortlist"]:
        print(f"- {c['name']} (Score: {c['score']}, CGPA: {c['cgpa']})")
        
    print("Unqualified candidates:")
    for c in results["unqualified_list"]:
        disq = c.get("disqualification_reason", "N/A")
        print(f"- {c['name']} (Score: {c['score']}, CGPA: {c['cgpa']}) | Disqualified: {disq}")
        
    # Assertions
    shortlist_names = [c["name"] for c in results["shortlist"]]
    unqualified_names = [c["name"] for c in results["unqualified_list"]]
    
    assert "Candidate A (Low CGPA)" not in shortlist_names, "Candidate A should be disqualified due to low CGPA!"
    assert "Candidate A (Low CGPA)" in unqualified_names, "Candidate A should be in the unqualified list!"
    assert results["unqualified_list"][0]["disqualification_reason"] == "Below CGPA minimum (6.0 required, candidate has 5.2)"
    
    print("\nCGPA enforcement unit test PASSED!")

if __name__ == "__main__":
    test_cgpa_enforcement()
