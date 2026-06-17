# tools.py
# Tool definitions for the QA Agent.
# Each tool maps to a GitHub REST API call or a local file read.
# Adding a new context source = adding a new tool here. No changes needed in qa_agent.py.
#
# Note on tool descriptions
# -------------------------
# As of 2026-05-21, tool descriptions are intentionally neutralized.
# Earlier versions included "Use this to..." hints that suggested when each
# tool should be called (e.g., "Use this to understand what problems have
# been reported"). Those hints were embedding QA-style usage guidance into
# the tool layer, which made it impossible to attribute the agent's
# exploration behavior cleanly to the prompt.
#
# Current descriptions are purely functional: what the tool does and what
# it returns. The agent is left to infer when each tool is useful.

import os
import requests
from pathlib import Path


GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO  = os.getenv("GITHUB_REPO", "betty-test-projects/qa-autonomy-project")
GITHUB_API   = "https://api.github.com"
GITHUB_HEADERS = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


# ---------------------------------------------------------------------------
# Tool definitions (sent to Claude API)
# Descriptions describe what the tool does, not when to use it.
# ---------------------------------------------------------------------------

TOOL_DEFINITIONS = [
    {
        "name": "get_issues",
        "description": (
            "Fetch issues from the GitHub repository. "
            "Returns issue number, title, body, labels, and state. "
            "Pull requests are excluded."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "description": "Filter by issue state. Default is 'open'.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_file_content",
        "description": (
            "Read the content of a specific file from the local codebase. "
            "Available files: app.py (Flask backend), templates/index.html (frontend)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": (
                        "Relative path to the file from the project root. "
                        "Examples: 'app.py', 'templates/index.html'"
                    ),
                }
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "get_commits",
        "description": (
            "Fetch recent commits from the GitHub repository. "
            "Returns commit message, author, date, and SHA."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Number of recent commits to fetch. Default is 10.",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_commit_diff",
        "description": (
            "Fetch the diff (changed files and lines) for a specific commit."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "sha": {
                    "type": "string",
                    "description": "The commit SHA to fetch the diff for.",
                }
            },
            "required": ["sha"],
        },
    },
]


# ---------------------------------------------------------------------------
# Tool execution (called when Claude decides to use a tool)
# Each function returns a string — that string becomes the tool result
# Claude sees in the next turn.
# ---------------------------------------------------------------------------

def execute_tool(tool_name: str, tool_input: dict) -> str:
    """
    Route a tool call to the appropriate function.
    Returns a string result that will be sent back to Claude.
    """
    handlers = {
        "get_issues":       _handle_get_issues,
        "get_file_content": _handle_get_file_content,
        "get_commits":      _handle_get_commits,
        "get_commit_diff":  _handle_get_commit_diff,
    }

    handler = handlers.get(tool_name)
    if not handler:
        return f"Error: Unknown tool '{tool_name}'"

    try:
        return handler(tool_input)
    except Exception as e:
        return f"Error executing {tool_name}: {str(e)}"


def _handle_get_issues(params: dict) -> str:
    """Fetch issues from GitHub. Excludes pull requests."""
    state = params.get("state", "open")
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/issues"
    resp = requests.get(url, headers=GITHUB_HEADERS, params={"state": state, "per_page": 50})

    if resp.status_code != 200:
        return f"GitHub API error {resp.status_code}: {resp.text}"

    issues = [i for i in resp.json() if "pull_request" not in i]

    if not issues:
        return f"No {state} issues found in {GITHUB_REPO}."

    result = []
    for issue in issues:
        labels = ", ".join(l["name"] for l in issue.get("labels", [])) or "none"
        body = issue.get("body") or "(no description)"
        # Truncate long bodies to keep context manageable
        if len(body) > 1000:
            body = body[:1000] + "... (truncated)"
        result.append(
            f"Issue #{issue['number']}: {issue['title']}\n"
            f"  State: {issue['state']} | Labels: {labels}\n"
            f"  URL: {issue['html_url']}\n"
            f"  Body: {body}\n"
        )

    return f"Found {len(issues)} {state} issue(s):\n\n" + "\n".join(result)


def _handle_get_file_content(params: dict) -> str:
    """Read a file from the local project directory."""
    file_path = params.get("file_path", "")
    project_root = Path(__file__).parent.parent

    # Security: prevent path traversal
    target = (project_root / file_path).resolve()
    if not str(target).startswith(str(project_root.resolve())):
        return f"Error: Access denied. Path '{file_path}' is outside the project directory."

    if not target.exists():
        return f"File not found: {file_path}"

    if not target.is_file():
        return f"Not a file: {file_path}"

    content = target.read_text(encoding="utf-8")

    # Truncate very large files
    if len(content) > 30000:
        content = content[:30000] + "\n... (truncated, file is very large)"

    return f"Content of {file_path}:\n\n{content}"


def _handle_get_commits(params: dict) -> str:
    """Fetch recent commits from GitHub."""
    limit = params.get("limit", 10)
    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/commits"
    resp = requests.get(url, headers=GITHUB_HEADERS, params={"per_page": limit})

    if resp.status_code != 200:
        return f"GitHub API error {resp.status_code}: {resp.text}"

    commits = resp.json()

    if not commits:
        return f"No commits found in {GITHUB_REPO}."

    result = []
    for c in commits:
        commit = c["commit"]
        author = commit["author"]["name"]
        date = commit["author"]["date"]
        message = commit["message"]
        sha = c["sha"][:7]
        result.append(f"[{sha}] {date} ({author}): {message}")

    return f"Recent {len(commits)} commit(s):\n\n" + "\n".join(result)


def _handle_get_commit_diff(params: dict) -> str:
    """Fetch the diff for a specific commit."""
    sha = params.get("sha", "")
    if not sha:
        return "Error: commit SHA is required."

    url = f"{GITHUB_API}/repos/{GITHUB_REPO}/commits/{sha}"
    resp = requests.get(url, headers=GITHUB_HEADERS)

    if resp.status_code != 200:
        return f"GitHub API error {resp.status_code}: {resp.text}"

    data = resp.json()
    files = data.get("files", [])

    if not files:
        return f"No file changes found in commit {sha}."

    result = []
    for f in files:
        patch = f.get("patch", "(binary or too large)")
        # Truncate large diffs
        if len(patch) > 3000:
            patch = patch[:3000] + "\n... (truncated)"
        result.append(
            f"File: {f['filename']} ({f['status']}, +{f['additions']}/-{f['deletions']})\n"
            f"{patch}\n"
        )

    return f"Diff for commit {sha[:7]}:\n\n" + "\n---\n".join(result)
