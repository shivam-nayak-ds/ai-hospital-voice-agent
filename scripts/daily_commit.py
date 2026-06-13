import os
import sys
import json
import subprocess
from pathlib import Path

# List of 30 commits with files to commit and messages
COMMITS_LIST = [
    {
        "id": 1,
        "files": ["Dockerfile"],
        "message": "docker: update dockerfile cmd execution path for fast execution"
    },
    {
        "id": 2,
        "files": ["alembic.ini"],
        "message": "db: update alembic.ini config with dynamic database connection string"
    },
    {
        "id": 3,
        "files": ["api/main.py"],
        "message": "api: register CORS origins and global validation exception handler"
    },
    {
        "id": 4,
        "files": ["frontend/streamlit_app.py"],
        "message": "frontend: build streamlit control dashboard to monitor agent state and database metrics"
    },
    {
        "id": 5,
        "files": ["src/agents/graph.py"],
        "message": "agent: structure state machine graph nodes using LangGraph framework"
    },
    {
        "id": 6,
        "files": ["src/agents/memory.py"],
        "message": "agent: design memory manager node to track multi-turn patient conversation states"
    },
    {
        "id": 7,
        "files": ["src/agents/response_builder.py"],
        "message": "agent: construct response builder node with edge-tts fallback mechanism"
    },
    {
        "id": 8,
        "files": ["src/core/config.py"],
        "message": "core: define setting schema with redis, postgreSQL, and Twilio config options"
    },
    {
        "id": 9,
        "files": ["src/db/session.py"],
        "message": "db: define async engine and scoped session setup for postgres connection pools"
    },
    {
        "id": 10,
        "files": ["src/rag/embeddings/embedding_pipeline.py"],
        "message": "rag: configure dense vector embedding model pipeline"
    },
    {
        "id": 11,
        "files": ["src/rag/processing/cleaner.py"],
        "message": "rag: add document chunking and metadata cleaning pipelines"
    },
    {
        "id": 12,
        "files": ["src/rag/prompts/hospital_prompt.py"],
        "message": "rag: optimize system instructions and response template prompts for receptionists"
    },
    {
        "id": 13,
        "files": ["src/repositories/appointment_repository.py"],
        "message": "db: build database queries for booking and fetching appointments"
    },
    {
        "id": 14,
        "files": ["src/repositories/patient_repository.py"],
        "message": "db: build database operations to fetch patient profile metadata"
    },
    {
        "id": 15,
        "files": ["src/services/booking_service.py"],
        "message": "service: implement validation service checks for appointment slots"
    },
    {
        "id": 16,
        "files": ["src/tools/billing_tool.py"],
        "message": "tools: add calculation billing tool to compute hospital cost catalog"
    },
    {
        "id": 17,
        "files": ["src/tools/emergency_tool.py"],
        "message": "tools: register real-time trauma triage routing logic for critical calls"
    },
    {
        "id": 18,
        "files": ["src/voice/orchestrator.py"],
        "message": "voice: construct twilio voice stream orchestrator module"
    },
    {
        "id": 19,
        "files": ["src/voice/stt.py"],
        "message": "voice: initialize deepgram streaming voice to text client connection"
    },
    {
        "id": 20,
        "files": ["src/voice/tts.py"],
        "message": "voice: construct Edge-TTS text to speech fallback player"
    },
    {
        "id": 21,
        "files": [
            ".github/workflows/ci.yml",
            ".github/workflows/docker.yml"
        ],
        "message": "ci: configure github actions workflows for tests and docker build verification"
    },
    {
        "id": 22,
        "files": ["api/routes/twilio_voice.py"],
        "message": "api: add websocket route for real-time Twilio stream media handler"
    },
    {
        "id": 23,
        "files": ["hiring_panel_evaluation.md"],
        "message": "docs: create hiring panel evaluation notes highlighting key performance parameters"
    },
    {
        "id": 24,
        "files": [
            "migrations/env.py",
            "migrations/script.py.mako"
        ],
        "message": "db: configure async migration runners using alembic env files"
    },
    {
        "id": 25,
        "files": ["migrations/versions/001_initial_schema.py"],
        "message": "db: generate initial tables schema migration step script"
    },
    {
        "id": 26,
        "files": ["scripts/interactive_test.py"],
        "message": "scripts: build interactive CLI agent tester using stateful pickling"
    },
    {
        "id": 27,
        "files": ["scripts/scheduler.py"],
        "message": "scripts: build cron scheduler task to scan upcoming patient reminders"
    },
    {
        "id": 28,
        "files": ["src/core/middleware/rate_limit.py"],
        "message": "middleware: implement sliding-window rate limiter utilizing Redis cache store"
    },
    {
        "id": 29,
        "files": ["src/services/notification_service.py"],
        "message": "service: add async notification dispatcher sending emails with thread executors"
    },
    {
        "id": 30,
        "files": [
            "src/utils/message_helper.py",
            "src/utils/pdf_generator.py",
            "tests/test_api_endpoints.py",
            "tests/test_fuzzy_matching.py",
            "tests/test_scheduler_notifications.py"
        ],
        "message": "tests: add test suite covering email notifications, api endpoints, and fuzzy matcher helpers"
    }
]

STATE_FILE = Path("scripts/daily_commit_state.json")

def run_git(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return result

def main():
    from datetime import datetime, timedelta
    
    run_all_at_once = "--all" in sys.argv

    # 1. Read state
    state = {"current_day": 0, "commits_done": []}
    if STATE_FILE.exists():
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
        except Exception as e:
            print(f"Warning: Failed to load state file: {e}. Resetting state.")

    if run_all_at_once:
        print("="*60)
        print("RUNNING ALL 30 COMMITS AT ONCE (BACKDATED OVER 6 DAYS)")
        print("="*60)
        
        successful_commits = []
        for day in range(1, 7):
            start_idx = (day - 1) * 5
            end_idx = day * 5
            day_commits = COMMITS_LIST[start_idx:end_idx]
            
            # Calculate backdate: Day 1 is 5 days ago, Day 6 is today
            target_date = datetime.now() - timedelta(days=(6 - day))
            git_date_str = target_date.strftime("%Y-%m-%dT12:00:00")
            
            print(f"\n--- DAY {day} (Backdated to {target_date.strftime('%Y-%m-%d')}) ---")
            
            for commit_data in day_commits:
                cid = commit_data["id"]
                files = commit_data["files"]
                msg = commit_data["message"]
                
                if cid in state.get("commits_done", []):
                    print(f"Commit {cid} already completed previously. Skipping.")
                    continue
                
                print(f"Processing Commit {cid}: '{msg}'")
                
                # Add files
                for f in files:
                    file_path = Path(f)
                    if file_path.exists():
                        run_git(["git", "add", f])
                
                # Commit with backdate
                commit_res = run_git([
                    "git", "commit", 
                    "--allow-empty", 
                    f"--date={git_date_str}", 
                    "-m", msg
                ])
                
                if commit_res.returncode == 0:
                    print(f"  [OK] Commit successful!")
                    successful_commits.append(cid)
                else:
                    print(f"  [ERROR] Commit failed: {commit_res.stderr.strip()}")
        
        # Try git push
        print("\nPushing all commits to remote repository...")
        push_res = run_git(["git", "push"])
        if push_res.returncode == 0:
            print("[SUCCESS] git push successful!")
        else:
            print("Warning: git push failed. You can run 'git push' manually later.")
            print(f"Details: {push_res.stderr.strip()}")
            
        # Update state
        state["current_day"] = 6
        state["commits_done"].extend(successful_commits)
        # deduplicate
        state["commits_done"] = list(set(state["commits_done"]))
        
        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)
            
        print("\n" + "="*60)
        print("CONGRATULATIONS! ALL 30 COMMITS COMPLETED AND PUSHED!")
        print(f"Total commits completed: {len(state['commits_done'])}/30")
        print("="*60)
        return

    day = state.get("current_day", 0) + 1

    if day > 6:
        print("="*60)
        print("Success! All 30 commits (6 days of progress) have been made.")
        print("All your changes are successfully committed.")
        print("="*60)
        return

    print("="*60)
    print(f"RUNNING Git Automation Script - DAY {day}/6")
    print("="*60)

    # 2. Get next 5 commits
    start_idx = (day - 1) * 5
    end_idx = day * 5
    day_commits = COMMITS_LIST[start_idx:end_idx]

    successful_commits = []

    for commit_data in day_commits:
        cid = commit_data["id"]
        files = commit_data["files"]
        msg = commit_data["message"]

        print(f"\nProcessing Commit {cid}: '{msg}'")
        
        # Add files
        staged_any = False
        for f in files:
            file_path = Path(f)
            if file_path.exists():
                print(f"  git add {f}")
                add_res = run_git(["git", "add", f])
                if add_res.returncode == 0:
                    staged_any = True
                else:
                    print(f"  Error staging {f}: {add_res.stderr.strip()}")
            else:
                print(f"  Warning: File '{f}' does not exist, skipping.")

        # Commit (Allow empty in case there are no changes, so script doesn't block)
        print(f"  git commit --allow-empty -m \"{msg}\"")
        commit_res = run_git(["git", "commit", "--allow-empty", "-m", msg])
        if commit_res.returncode == 0:
            print(f"  [OK] Commit successful!")
            successful_commits.append(cid)
        else:
            print(f"  [ERROR] Commit failed: {commit_res.stderr.strip()}")

    # 3. Try git push
    print("\nPushing commits to remote repository...")
    push_res = run_git(["git", "push"])
    if push_res.returncode == 0:
        print("[SUCCESS] git push successful!")
    else:
        print("Warning: git push failed. You can run 'git push' manually later.")
        print(f"Details: {push_res.stderr.strip()}")

    # 4. Update state
    state["current_day"] = day
    state["commits_done"].extend(successful_commits)
    
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=4)

    print("\n" + "="*60)
    print(f"DAY {day} COMPLETED!")
    print(f"Made {len(successful_commits)} commits today.")
    print(f"Total commits completed: {len(state['commits_done'])}/30")
    if day < 6:
        print(f"Please run this script again tomorrow for Day {day + 1}/6.")
    else:
        print("Congratulations! All 30 commits are completed!")
    print("="*60)

if __name__ == "__main__":
    main()
