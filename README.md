\# LLM-Powered Code Generation and Deployment Pipeline



\## 1. Project Overview



This project is a fully automated application that receives a request to build a web application, uses a Large Language Model (LLM) to generate the code, and deploys the resulting site to GitHub Pages. The system is built with Python, using FastAPI for the API server and the PyGithub library to interact with the GitHub API. It is designed to be robust, secure, and resilient to common issues like API delays.



\## 2. Core Features



\-   \*\*API Server\*\*: A FastAPI endpoint listens for incoming JSON build requests and processes them in the background.

\-   \*\*Secure\*\*: The endpoint is secured with a shared secret. All API keys and tokens are managed safely via a `.env` file and are never committed to the repository, as enforced by the `.gitignore` file.

\-   \*\*LLM Integration\*\*: Utilizes the OpenRouter API to generate code via powerful models like Google's Gemini 2.5 Pro.

\-   \*\*Automated Git Operations\*\*: Creates new public GitHub repositories and commits the generated code, a professional README, and a LICENSE file programmatically.

\-   \*\*Resilient Deployment\*\*: Includes intelligent polling mechanisms to handle delays in the GitHub Pages API, ensuring a more reliable deployment process.

\-   \*\*Evaluation Ping\*\*: Automatically notifies an external evaluation server upon successful deployment, sending all required metadata.



\## 3. How to Set Up and Run



\### Prerequisites

\- Python 3.10+

\- A GitHub account with a Personal Access Token (PAT)

\- An OpenRouter API key



\### Step 1: Install Dependencies

Clone the repository and install the required Python packages.

pip install -r requirements.txt



text



\### Step 2: Set Up Environment Variables

Create a `.env` file in the root directory of the project. You can use the `.env.example` file as a template. Populate it with your credentials:

GITHUB\_TOKEN=your\_github\_personal\_access\_token

GITHUB\_USERNAME=your\_github\_username

OPENROUTER\_API\_KEY=your\_openrouter\_api\_key

MY\_SECRET=your\_chosen\_secret\_for\_the\_api



text



\### Step 3: Run the Application

1\.  \*\*Start the API Server\*\*:

&nbsp;   ```

&nbsp;   uvicorn main:app --host 0.0.0.0 --port 8000

&nbsp;   ```

2\.  \*\*Expose the Endpoint\*\*: Use a service like ngrok to create a public URL for your local server, which is required for the evaluation system to reach your API.

&nbsp;   ```

&nbsp;   ngrok http 8000

&nbsp;   ```

&nbsp;   Ngrok will provide a public "Forwarding" URL (e.g., `https://<random-string>.ngrok-free.dev`). Your full API endpoint will be this URL plus `/api-endpoint`.



\## 4. How to Test the System

The `test\_complete.py` script is provided to simulate a request from the evaluation server.

1\.  Ensure your server and ngrok tunnel are running.

2\.  Update the `ENDPOINT` variable in `test\_complete.py` with your current ngrok URL.

3\.  Run the test script:

&nbsp;   ```

&nbsp;   python test\_complete.py

&nbsp;   ```

You can monitor the terminal running `main.py` to see the live logs of the build and deployment process.



\## 5. Project Structure

\-   `main.py`: The core FastAPI application containing all automation logic.

\-   `test\_complete.py`: The script used to perform end-to-end testing.

\-   `requirements.txt`: A list of all Python dependencies for the project.

\-   `README.md`: This documentation file.

\-   `.gitignore`: Specifies files and folders to be ignored by Git (e.g., `.env`, `\_\_pycache\_\_/`).

\-   `.env.example`: A template for the required environment variables.

\-   `LICENSE`: The MIT License for the project.

