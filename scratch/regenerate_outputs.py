import os
import sys
import shutil
import subprocess

def run_cmd(args):
    print(f"Running: {' '.join(args)}")
    proc = subprocess.run(args, capture_output=True, text=True)
    if proc.returncode != 0:
        print(f"Error executing command: {proc.stderr}")
        sys.exit(1)

def regenerate():
    # 1. Clean output directories
    dirs_to_clean = ["output_results", "test_run_1", "test_run_2", "test_run_3"]
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Deleting stale directory: {d}")
            shutil.rmtree(d)
            
    python_exe = sys.executable
    jds = ["frontend_developer", "backend_developer", "full_stack_developer", "database_developer", "api_integration_developer"]
    
    # 2. Run for the 5 JDs for output_results
    for jd in jds:
        print(f"\nRegenerating results for JD: {jd}")
        args = [
            python_exe, "main.py",
            "--input", "resumes",
            "--jd", jd,
            "--output", "output_results"
        ]
        run_cmd(args)
        
    # 3. Run determinism test script (which creates test_run_1/2/3 and runs checks)
    print("\nRunning test_engine.py to verify score determinism and recreate test_run folders...")
    args_test = [python_exe, "test_engine.py"]
    run_cmd(args_test)
    
    # 4. Verify candidate counts in all generated results
    print("\n=== Verifying Candidate Counts ===")
    import json
    for jd in jds:
        path = f"output_results/{jd}_results.json"
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            total = len(data.get("shortlist", [])) + len(data.get("reserve_list", [])) + len(data.get("unqualified_list", [])) + len(data.get("failed_list", []))
            print(f"JD: {jd} | Total evaluated candidates = {total}")
            
if __name__ == "__main__":
    regenerate()
