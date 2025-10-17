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

# --- Load credentials ---
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
    except UnknownObjectException:
        print(f"File '{path}' not found. Creating new file.")
        repo.create_file(path, message, content)
    except Exception as e:
        print(f"An error occurred while creating/updating file {path}: {e}")
        raise

def generate_code(brief, checks, round_num, attachments=None, existing_code=None):
    """Generates or updates HTML code using an LLM, with support for attachments."""
    print("Calling OpenRouter API (Google Gemini 2.5 Pro)...")
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OPENROUTER_API_KEY,
    )

    checks_text = "\n".join(f"- {check}" for check in checks)
    
    # **FIX 1: Process attachments and add them to the prompt**
    attachment_text = ""
    if attachments:
        attachment_files = []
        for attachment in attachments:
            try:
                header, encoded = attachment['url'].split(",", 1)
                file_content = base64.b64decode(encoded).decode('utf-8')
                attachment_files.append(f"File `{attachment['name']}` content:\n``````")
            except Exception as e:
                print(f"Warning: Could not decode attachment {attachment['name']}: {e}")
        if attachment_files:
            attachment_text = "\n\nUse the following file(s) as context:\n" + "\n\n".join(attachment_files)

    # **FIX 2: Correctly format prompts for Round 1 and Round 2**
    if round_num == 1:
        prompt = (
            f"Create a single, complete HTML file for this task: {brief}.\n\n"
            f"It must pass these checks:\n{checks_text}{attachment_text}\n\n"
            "Output ONLY the raw HTML code."
        )
    else:  # Round 2
        prompt = (
            f"Update this existing HTML code:\n``````\n\n"
            f"New task brief: {brief}\n\n"
            f"New checks:\n{checks_text}{attachment_text}\n\n"
            "Output ONLY the updated, raw HTML code."
        )

    response = client.chat.completions.create(
        model="google/gemini-2.5-pro",
        messages=[{"role": "user", "content": prompt}]
    )

    code = response.choices[0].message.content.strip()

    if code.startswith("```
        first_newline = code.find('\n')
        code = code[first_newline + 1:] if first_newline != -1 else ""
    if code.endswith("```"):
        code = code[:-3].strip()
    
    print("Code generated successfully.")
    return code

def generate_readme(repo_name, brief, checks, round_num):
    """Generates a professional README.md."""
    # (This function can be expanded for more detail)
    return f"# {repo_name.replace('-', ' ').title()}\n\n**Task Brief (Round {round_num}):**\n{brief}"

def enable_and_verify_pages(repo):
    """Enables GitHub Pages and waits for it to become live."""
    # (This is a robust function, no changes needed here)
    print("Enabling GitHub Pages...")
    owner, repo_name = repo.full_name.split('/')
    pages_url = f"https://{owner}.github.io/{repo_name}/"
    api_url = f"https://api.github.com/repos/{owner}/{repo_name}/pages"
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    payload = {"source": {"branch": "main", "path": "/"}}

    for attempt in range(6): # Try for up to ~60 seconds
        response = requests.put(api_url, json=payload, headers=headers, timeout=30)
        if response.status_code in [201, 204]:
            print("GitHub Pages enabled successfully via API.")
            break
        time.sleep(2 ** attempt)
    
    print(f"Verifying deployment at {pages_url}...")
    for _ in range(8): # Check for up to ~4 minutes
        try:
            if requests.head(pages_url, timeout=15).status_code == 200:
                print("GitHub Pages site is live!")
                return pages_url
        except requests.RequestException:
            pass
        time.sleep(30)
    print("Warning: Pages URL could not be verified in time, but proceeding.")
    return pages_url

def notify_eval(url, payload):
    """Notifies the evaluation server with exponential backoff."""
    # (This is a robust function, no changes needed here)
    print(f"Notifying evaluation server at {url}...")
    for attempt in range(5):
        try:
            response = requests.post(url, json=payload, timeout=30)
            if response.status_code == 200:
                print("Notification sent successfully.")
                return
        except requests.RequestException as e:
            print(f"Attempt {attempt+1} failed: {e}")
        time.sleep(2 ** attempt)

# --- Main Processing Logic ---

def process_task(data):
    """The core function to handle build and revise requests."""
    try:
        print(f"{'='*60}\nSTARTED for Task: {data['task']}, Round: {data['round']}\n{'='*60}")
        
        auth = Auth.Token(GITHUB_TOKEN)
        g = Github(auth=auth)
        user = g.get_user()
        
        repo_name = f"tds-{data['task'].replace('.', '-')}"

        try:
            repo = g.get_repo(f"{GITHUB_USERNAME}/{repo_name}")
            print(f"Using existing repo: {repo_name}")
        except UnknownObjectException:
            if data['round'] == 1:
                print(f"Repo {repo_name} not found. Creating it.")
                repo = user.create_repo(repo_name, description="TDS Auto-generated App", private=False)
            else:
                print(f"FATAL ERROR: Repo {repo_name} not found for Round {data['round']}.")
                return

        # **FIX 3: Fetch existing code for Round 2**
        existing_code = None
        if data['round'] > 1:
            try:
                content_file = repo.get_contents("index.html")
                existing_code = content_file.decoded_content.decode("utf-8")
                print("Fetched existing index.html for Round 2 update.")
            except UnknownObjectException:
                print("Warning: index.html not found for Round 2. A new file will be created.")
        
        # **Call the updated generate_code function**
        html_code = generate_code(
            data['brief'],
            data['checks'],
            data['round'],
            attachments=data.get('attachments'),
            existing_code=existing_code
        )

        create_or_update_file(repo, "index.html", f"feat: Update for round {data['round']}", html_code)
        
        if data['round'] == 1:
             # Add license only on first round
            license_content = requests.get("https://api.github.com/licenses/mit").json()['body']
            create_or_update_file(repo, "LICENSE", "docs: Add MIT License", license_content)

        readme_content = generate_readme(repo_name, data['brief'], data['checks'], data['round'])
        create_or_update_file(repo, "README.md", f"docs: Update README for round {data['round']}", readme_content)

        pages_url = enable_and_verify_pages(repo)
        commit_sha = repo.get_branch("main").commit.sha

        payload = {
            "email": data["email"], "task": data["task"], "round": data["round"],
            "nonce": data["nonce"], "repo_url": repo.html_url,
            "commit_sha": commit_sha, "pages_url": pages_url
        }
        notify_eval(data["evaluation_url"], payload)

    except Exception as e:
        print(f"\nAn unhandled exception occurred in process_task: {e}")
        traceback.print_exc()
    finally:
        print(f"\n{'='*60}\nPROCESS FINISHED\n{'='*60}")

# --- FastAPI Endpoints ---

@app.get("/")
async def root():
    return {"message": "Server is running."}

@app.post("/api-endpoint")
async def handle_request(request: Request, background_tasks: BackgroundTasks):
    try:
        data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON.")
    
    if data.get("secret") != MY_SECRET:
        raise HTTPException(status_code=403, detail="Invalid secret.")
    
    background_tasks.add_task(process_task, data)
    return {"status": "Request accepted."}

if __name__ == "__main__":
    import uvicorn
    print("Server starting...")
    uvicorn.run(app, host="0.0.0.0", port=8000)


