import urllib.request
import json
import os

TOKEN = os.getenv("GITHUB_TOKEN")
REPO = "Reddy0402/software-dna"

ISSUES = [
    {
        "title": "Repository Import",
        "body": "Implement module to import and synchronize Git repositories into the system, including handling branch checkouts and local/remote sync."
    },
    {
        "title": "Parser Engine",
        "body": "Build the core syntax parsing engine to support multiple programming languages and orchestrate parser tasks."
    },
    {
        "title": "AST Extraction",
        "body": "Extract Abstract Syntax Trees (AST) from source files to capture rich syntax structure, variables, functions, and import metadata."
    },
    {
        "title": "Dependency Graph",
        "body": "Construct dependency graphs mapping the relationships and call chains between files, packages, classes, and modules."
    },
    {
        "title": "Knowledge Graph",
        "body": "Integrate AST structures, dependencies, git history, and developer metadata into a unified knowledge graph."
    },
    {
        "title": "Neo4j Integration",
        "body": "Set up Neo4j database integration to store, persist, and query the software knowledge graph efficiently."
    },
    {
        "title": "DNA Model",
        "body": "Define the core 'DNA Model' schema representing software systems as living, dynamic digital organisms."
    },
    {
        "title": "Developer Analytics",
        "body": "Implement developer analytics metrics to evaluate code authorship, knowledge silos, and project collaboration patterns."
    },
    {
        "title": "Repository Search",
        "body": "Create a semantic code search engine to enable fast, intelligence-driven querying of the codebase."
    },
    {
        "title": "AI Chat",
        "body": "Integrate an LLM-powered interactive chat assistant that answers architecture and code-level queries about the repository."
    },
    {
        "title": "Impact Analysis",
        "body": "Create an impact analysis feature to simulate code edits and predict downstream effects and dependencies."
    },
    {
        "title": "Risk Prediction",
        "body": "Develop models to identify high-risk code changes, potential bug hotspots, and areas of high technical debt."
    },
    {
        "title": "Documentation",
        "body": "Author user guides, system architecture designs, and API reference documentation for developers and users."
    },
    {
        "title": "Deployment",
        "body": "Configure CI/CD pipelines, Docker container setups, and local/production infrastructure deployments."
    }
]

def create_issue(issue):
    url = f"https://api.github.com/repos/{REPO}/issues"
    headers = {
        "Authorization": f"Bearer {TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/json",
        "User-Agent": "Software-DNA-Issue-Creator"
    }
    
    data = json.dumps(issue).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers=headers, method='POST')
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            print(f"Successfully created issue #{res_data.get('number')}: {res_data.get('title')}")
    except Exception as e:
        print(f"Failed to create issue '{issue['title']}': {e}")

if __name__ == "__main__":
    if not TOKEN:
        print("Error: GITHUB_TOKEN environment variable is not set.")
        exit(1)
    print(f"Creating {len(ISSUES)} issues on {REPO}...")
    for issue in ISSUES:
        create_issue(issue)
