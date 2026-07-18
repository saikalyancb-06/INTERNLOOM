import subprocess
import json
import os
import sys

def get_scores_from_json(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    scores = {}
    for group in ["shortlist", "reserve_list", "unqualified_list"]:
        for cand in data.get(group, []):
            scores[cand["filename"]] = cand["score"]
    return scores

def main():
    print("Running determinism tests: running shortlisting engine 3 times...")
    python_exe = sys.executable
    
    # Files to compare
    runs = 3
    results_scores = []
    
    for run in range(1, runs + 1):
        print(f"Executing run {run}/3...")
        out_dir = f"test_run_{run}"
        cmd = [
            python_exe, "main.py",
            "--input", "resumes",
            "--jd", "frontend_developer",
            "--output", out_dir
        ]
        
        # Run process
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            print(f"Error during run {run}: {proc.stderr}")
            sys.exit(1)
            
        json_path = os.path.join(out_dir, "frontend_developer_results.json")
        scores = get_scores_from_json(json_path)
        results_scores.append(scores)
        
    # Check for score drift between runs
    drift_detected = False
    first_run_scores = results_scores[0]
    
    for idx, run_scores in enumerate(results_scores[1:], start=2):
        for candidate, score in first_run_scores.items():
            if candidate not in run_scores:
                print(f"Error: Candidate '{candidate}' missing in run {idx}!")
                drift_detected = True
                continue
            diff = abs(score - run_scores[candidate])
            if diff > 0.0:
                print(f"Drift detected for '{candidate}': Run 1 = {score}, Run {idx} = {run_scores[candidate]} (Diff = {diff})")
                drift_detected = True
                
    if not drift_detected:
        print("\nDeterminism check passed! Absolute score stability verified across 3 successive runs (Drift = 0.0).")
    else:
        print("\nDeterminism check failed. Scores drifted.")
        sys.exit(1)

if __name__ == "__main__":
    main()
