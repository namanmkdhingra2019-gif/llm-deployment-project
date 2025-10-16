import os
import time
import requests
import base64
import re
import traceback
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from dotenv import load_dotenv
from github import Github, Auth, UnknownObjectException, GithubException
from openai import OpenAI

# --- Environment Setup ---
load_dotenv()
app = FastAPI()

# Load credentials
MY_SECRET = os.environ.get("MY_SECRET")
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
GITHUB_USERNAME = os.environ.get("GITHUB_USERNAME")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")

# --- Utility Functions ---

def create_or_update_file(repo, path, message, content):
    """Creates a file if it doesn't exist, or updates it if it does."""
    try:
        existing_file = repo.get_contents(path)
        repo.update_file(path, message, content, existing_file.sha)
        print(f"Updated file: {path}")
    except GithubException as e:
        if e.status == 404:
            print(f"File '{path}' not found or repo is empty. Creating file.")
            repo.create_file(path, message, content)
        else:
            raise

def generate_code(brief, checks, round_num, existing_code=None):
    """Generates HTML code using an LLM."""
    print("Calling OpenRouter API (Google Gemini 2.5 Pro)...")
    client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=OPENROUTER_API_KEY)
    
    checks_text = "\n".join(f"- {check}" for check in checks)
    
    if round_num == 1:
        prompt = f"Create a single, complete HTML file for this task: {brief}. It must pass these checks: {checks_text}. Output ONLY the raw HTML code."
    else: # Round 2
        prompt = f"Update this HTML code: ``````. New task: {brief}. New checks: {checks_text}. Output ONLY the updated, raw HTML code."

    response = client.chat.completions.create(model="google/gemini-2.5-pro", messages=[{"role": "user", "content": prompt}])
    
    code = response.choices[0].message.content.strip()
    
    if code.startswith("```"): 
        first_newline = code.find('\n')
        code = code[first_newline + 1:] if first_newline != -1 else code[3:]
    if code.endswith("```"):
        code = code[:-3].strip()
        
    print("Code generated successfully.")
    return code

def generate_readme(repo_name, brief, checks, round_num):
    return f"# {repo_name.replace('-', ' ').title()}\n## Task\n> {brief}\n## Live Demo\n[https://{GITHUB_USERNAME}.github.io/{repo_name}/](https://{GITHUB_USERNAME}.github.io/{repo_name}/)"

def enable_and_verify_pages(repo):
    """Enables GitHub Pages with polling to handle API delays."""
    print("Enabling GitHub Pages...")
    owner, repo_name = repo.full_name.split('/')
    pages_url = f"https://{owner}.github.io/{repo_name}/"
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/pages"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github+json"}
    payload = {"source": {"branch": "main", "path": "/"}}

    # --- INTELLIGENT POLLING LOGIC ---
    for attempt in range(6): # Try for up to ~60 seconds
        response = requests.put(api_url, json=payload, headers=headers, timeout=30)
        if response.status_code in [201, 204]:
            print("GitHub Pages enabled successfully via API.")
            break
        elif response.status_code == 404:
            print(f"Attempt {attempt+1}/6: Repo not yet found by Pages API. Retrying in {2**attempt}s...")
            time.sleep(2**attempt)
        else:
            print(f"Warning: Unexpected error enabling Pages. Status: {response.status_code}, Body: {response.text}")
            break
    else:
        print("Warning: Could not enable GitHub Pages via API after multiple attempts.")

    print(f"Verifying deployment at {pages_url}...")
    for i in range(8): # Check for up to ~4 minutes
        try:
            if requests.head(pages_url, timeout=15).status_code == 200:
                print("GitHub Pages site is live!")
                return pages_url
        except requests.RequestException: pass
        time.sleep(2 ** i)
    print("Warning: Pages URL could not be verified in time, but proceeding.")
    return pages_url

def notify_eval(url, payload):
    # ... (This function is already robust) ...
    print(f"Notifying evaluation server at {url}...")
    for attempt in range(5):
        try:
            if requests.post(url, json=payload, timeout=30).status_code == 200:
                print("Notification sent successfully.")
                return
        except requests.RequestException as e: print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(2 ** attempt)

def process_task(data):
    try:
        print(f"\n{'='*60}\nBUILD STARTED for Task: {data['task']}, Round: {data['round']}\n{'='*60}")
        
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        user = g.get_user()
        
        repo_base_name = f"tds-{data['task']}".replace(".", "-")
        repo_name = f"{repo_base_name}-r1"

        try:
            repo = user.create_repo(name=repo_name, description="TDS Auto-generated App", private=False)
            print(f"Repository '{repo_name}' created.")
        except GithubException as e:
            if e.status == 422 and "name already exists" in str(e.data):
                print(f"Repo '{repo_name}' already exists. Using existing repo.")
                repo = g.get_repo(f"{GITHUB_USERNAME}/{repo_name}")
            else:
                raise

        html_code = generate_code(data['brief'], data.get('checks', []), 1)
        create_or_update_file(repo, "index.html", "feat: Add application code", html_code)
        
        readme_content = generate_readme(repo_name, data['brief'], data.get('checks', []), 1)

        create_or_update_file(repo, "README.md", "docs: Add project README", readme_content)
        
        create_or_update_file(repo, "LICENSE", "docs: Add MIT License", requests.get("https://api.github.com/licenses/mit").json()["body"])
        
        pages_url = enable_and_verify_pages(repo)
        commit_sha = repo.get_branch("main").commit.sha
        
        payload = { "email": data['email'], "task": data['task'], "round": data['round'], "nonce": data['nonce'], "repo_url": repo.html_url, "commit_sha": commit_sha, "pages_url": pages_url }
        notify_eval(data['evaluation_url'], payload)

    except Exception as e:
        print(f"\nERROR: An unhandled exception occurred: {e}")
        traceback.print_exc()
    finally:
        print(f"{'='*60}\nBUILD PROCESS FINISHED\n{'='*60}\n")

@app.get("/")
async def root(): return {"message": "Server is running."}

@app.post("/api-endpoint")
async def handle_request(request: Request, background_tasks: BackgroundTasks):
    try: data = await request.json()
    except Exception: raise HTTPException(status_code=400, detail="Invalid JSON.")
    if data.get("secret") != MY_SECRET: raise HTTPException(status_code=403, detail="Invalid secret.")
    
    background_tasks.add_task(process_task, data)
    return {"status": "Request accepted."}

if __name__ == "__main__":
    import uvicorn
    print("Server starting...")
    uvicorn.run(app, host="0.0.0.0", port=8000)


