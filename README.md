# When the Agent Chooses

A small experiment in QA agent autonomy.

The agent uses Claude API tool use to autonomously decide which tools to call —
issues, commits, and source code — when asked to assess a small target
repository. Two prompt versions are included: one that frames the agent as a
senior QA engineer, and one that strips all QA framing out.

This code accompanies a Medium article series of the same name. The articles
describe what was observed. This repo is for readers who would rather run it
themselves and see what they observe.

## What the agent can call

The agent has four tools available. Which ones it uses, in what order, and
when to stop is its own decision.

- `get_issues` — GitHub API, fetches open/closed issues from the target repo
- `get_commits` — GitHub API, fetches recent commit history
- `get_commit_diff` — GitHub API, fetches the diff for a specific commit
- `get_file_content` — reads source files from this local repository

Three tools talk to GitHub. `get_file_content` reads from disk — the Task
Manager source (`app.py`, `templates/index.html`) lives in this repo and the
agent inspects it locally.

## What's in this repo

```
qa-autonomy-project/
├── agent/
│   ├── qa_agent.py        # The agent loop
│   ├── tools.py           # Tool definitions and execution
│   └── prompts/
│       ├── __init__.py    # Loads prompt by PROMPT_VERSION env var
│       ├── v0.py          # Neutral prompt — no QA framing
│       └── v1.py          # QA-framed prompt — senior QA identity, classifications
├── templates/
│   └── index.html         # Task Manager frontend
├── app.py                 # Task Manager web app — Flask + SQLite
├── output/                # Agent reports written here (gitignored)
├── .env.example           # Template for environment variables
├── .gitignore
├── requirements.txt
├── LICENSE
└── README.md
```

## What's not in this repo, and why

The reports the agent produced during the experiment are deliberately not
committed.

The experiment compared two prompt versions, but each was run only once. That
is enough to observe behavior; it is not enough to claim one version
consistently produced a better report than the other. Committing the raw
single-run outputs would invite a comparison the experiment is not equipped
to support.

If you want to see what the agent produces, the more honest path is to run it
yourself.

## Setup

Requires Python 3.13. From the repo root:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env` and fill in:

```
ANTHROPIC_API_KEY=sk-ant-...
GITHUB_TOKEN=ghp_...
GITHUB_REPO=your-username/your-target-repo
PROMPT_VERSION=v1
```

The `GITHUB_TOKEN` needs read access to issues on the target repo. The default
model is `claude-haiku-4-5-20251001`; override it by setting `CLAUDE_MODEL` if
you want to use a different one.

`.env` is gitignored. Do not commit it.

## Running the experiment

The agent reads `PROMPT_VERSION` from the environment to decide which prompt
to use.

Run with the QA-framed prompt:

```bash
PROMPT_VERSION=v1 python agent/qa_agent.py
```

Run with the neutral prompt:

```bash
PROMPT_VERSION=v0 python agent/qa_agent.py
```

Reports are written to `output/qa_report_<version>_<timestamp>.md`. Every tool
call the agent makes is logged to the terminal as it happens, along with its
reasoning. The log is the more interesting part of the run.

## The two prompts

`v1.py` frames the agent as a senior QA engineer, gives it classification
vocabulary (`confirmed_bug` / `requirement_gap` / `weak_signal` /
`out_of_scope`), and provides four guiding questions about the codebase.

`v0.py` removes all of that. No identity. No QA vocabulary. The task is
described as analyzing a repository, without naming what kind of analysis.
The available tools are the same; only the prompt differs.

What changes when those words are removed is the experiment.

## The target app

A small Task Manager web app (Flask + SQLite + vanilla JS) is included as the
target for the agent to analyze. It has a handful of intentionally-filed
issues on its own GitHub repo.

You can run it locally:

```bash
python app.py
```

It listens on `http://localhost:5000`. The agent does not need the app to be
running — it reads from the GitHub repo, not from a live server.

## License

MIT. See `LICENSE`.
