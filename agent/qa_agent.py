# qa_agent.py
# QA Agent — uses Claude API tool use to let the AI autonomously decide
# what context to gather from GitHub and the local codebase.
#
# Key difference from a standard script: this agent does NOT pre-fetch data.
# Claude decides what to look at, in what order, and when to stop.
# Every tool call and its reasoning are logged for later observation.
#
# Flow:
#   1. Send task description + available tools to Claude
#   2. Claude calls tools autonomously (loop until it stops)
#   3. Log every tool call with reasoning
#   4. Write final report to output/
#   5. Print summary and wait for human review
#
# Prompt versioning:
#   Set the PROMPT_VERSION env var to choose which prompt to use.
#   Example: PROMPT_VERSION=v2 python agent/qa_agent.py
#   Defaults to v1 if not set. See prompts/ folder for available versions.

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

# Load env vars BEFORE importing tools.py and prompts/ —
# both read env vars at import time.
load_dotenv()

import anthropic

# PROMPT_VERSION is re-exported by prompts/__init__.py so it can be logged
# alongside the report. SYSTEM_PROMPT is dynamically selected by the env var.
from prompts import SYSTEM_PROMPT, PROMPT_VERSION
from tools import TOOL_DEFINITIONS, execute_tool

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("CLAUDE_MODEL", "claude-haiku-4-5-20251001")
GITHUB_REPO = os.getenv("GITHUB_REPO", "betty-test-projects/qa-autonomy-project")

OUTPUT_DIR = Path(__file__).parent.parent / "output"


# ---------------------------------------------------------------------------
# The agent loop
# ---------------------------------------------------------------------------

def run_agent() -> dict:
    """
    Run the autonomous QA agent.

    This function implements a tool-use loop:
    1. Send the task to Claude with available tools
    2. If Claude wants to call a tool, execute it and send the result back
    3. Repeat until Claude produces a final text response (no more tool calls)

    Returns a dict with:
      - "report": the final analysis text
      - "tool_log": list of every tool call made, in order
      - "total_input_tokens": cumulative input tokens
      - "total_output_tokens": cumulative output tokens
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # The initial message — deliberately open-ended.
    # We tell Claude WHAT to do, but not HOW to gather information.
    messages = [
        {
            "role": "user",
            "content": (
                f"Please assess the quality risks of the repository: {GITHUB_REPO}\n\n"
                "You have tools available to inspect GitHub issues, source code, "
                "and commit history. Decide what you need to look at and in what order.\n\n"
                "When you have gathered enough context, produce your QA assessment report."
            ),
        }
    ]

    tool_log = []
    total_input_tokens = 0
    total_output_tokens = 0
    iteration = 0
    max_iterations = 20  # Safety limit to prevent infinite loops

    print(f"\n{'='*60}")
    print(f"QA Agent starting")
    print(f"Repo:           {GITHUB_REPO}")
    print(f"Model:          {MODEL}")
    print(f"Prompt version: {PROMPT_VERSION}")
    print(f"{'='*60}\n")

    while iteration < max_iterations:
        iteration += 1
        print(f"[turn {iteration}] Sending request to Claude...")

        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )

        # Track token usage
        total_input_tokens += response.usage.input_tokens
        total_output_tokens += response.usage.output_tokens

        # Process response content blocks
        # Claude may return a mix of text and tool_use blocks
        assistant_content = response.content
        tool_calls_in_turn = []

        for block in assistant_content:
            if block.type == "text":
                print(f"[turn {iteration}] Claude says: {block.text[:120]}...")
            elif block.type == "tool_use":
                tool_calls_in_turn.append(block)
                print(f"[turn {iteration}] Claude calls: {block.name}({json.dumps(block.input)})")

        # If Claude is done (end_turn with no tool calls), we have the final report
        if response.stop_reason == "end_turn":
            final_text = ""
            for block in assistant_content:
                if block.type == "text":
                    final_text += block.text
            print(f"\n[done] Agent completed in {iteration} turn(s)")
            return {
                "report": final_text,
                "tool_log": tool_log,
                "total_input_tokens": total_input_tokens,
                "total_output_tokens": total_output_tokens,
            }

        # If Claude wants to use tools, execute them and send results back
        if response.stop_reason == "tool_use":
            # Add the assistant's response (including tool_use blocks) to messages
            messages.append({"role": "assistant", "content": assistant_content})

            # Execute each tool call and collect results
            tool_results = []
            for tool_call in tool_calls_in_turn:
                print(f"[exec] Running {tool_call.name}...")
                result = execute_tool(tool_call.name, tool_call.input)
                print(f"[exec] {tool_call.name} returned {len(result)} chars")

                # Log for observation
                tool_log.append({
                    "turn": iteration,
                    "tool": tool_call.name,
                    "input": tool_call.input,
                    "result_length": len(result),
                    "result_preview": result[:200],
                })

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_call.id,
                    "content": result,
                })

            # Send tool results back to Claude
            messages.append({"role": "user", "content": tool_results})

    # If we hit max iterations, return what we have
    print(f"\n[warn] Agent hit max iterations ({max_iterations})")
    return {
        "report": "(Agent reached maximum iterations without producing a final report)",
        "tool_log": tool_log,
        "total_input_tokens": total_input_tokens,
        "total_output_tokens": total_output_tokens,
    }


# ---------------------------------------------------------------------------
# Report writing
# ---------------------------------------------------------------------------

def write_report(result: dict) -> Path:
    """
    Write the agent's report and tool log to a timestamped markdown file.
    The tool log is the primary observation artifact for the experiment.

    Report filename includes the prompt version so multiple experiments
    can coexist in the same output folder without confusion.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_path = OUTPUT_DIR / f"qa_report_{PROMPT_VERSION}_{timestamp}.md"

    # Format the tool call log
    tool_log_text = ""
    if result["tool_log"]:
        for entry in result["tool_log"]:
            tool_log_text += (
                f"- **Turn {entry['turn']}**: `{entry['tool']}` "
                f"with input `{json.dumps(entry['input'])}` "
                f"→ {entry['result_length']} chars returned\n"
            )
    else:
        tool_log_text = "No tool calls were made.\n"

    report = f"""# QA Agent Report

Generated:      {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
Model:          {MODEL}
Prompt version: {PROMPT_VERSION}
Repo:           {GITHUB_REPO}

## Agent tool call log

This section records every tool the agent chose to call, in order.
This is the primary observation data for the experiment.

{tool_log_text}

## Token usage

- Input tokens:  {result['total_input_tokens']}
- Output tokens: {result['total_output_tokens']}

---

## Agent's QA Assessment

{result['report']}

---

*This report was generated by an autonomous QA agent.
All classifications and risk assessments require human review before any action is taken.*
"""

    report_path.write_text(report, encoding="utf-8")
    print(f"\n[output] Report written to {report_path}")
    return report_path


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    if not ANTHROPIC_API_KEY:
        print("[error] ANTHROPIC_API_KEY not set in .env")
        sys.exit(1)
    if not os.getenv("GITHUB_TOKEN"):
        print("[error] GITHUB_TOKEN not set in .env")
        sys.exit(1)

    result = run_agent()
    report_path = write_report(result)

    # Human checkpoint
    print(f"\n{'='*60}")
    print("HUMAN REVIEW REQUIRED")
    print(f"{'='*60}")
    print(f"\nReport:          {report_path}")
    print(f"Prompt version:  {PROMPT_VERSION}")
    print(f"Tool calls made: {len(result['tool_log'])}")
    print(f"Tokens used:     {result['total_input_tokens']} in / {result['total_output_tokens']} out")
    print(f"\nReview the report. Key questions to consider:")
    print(f"  - What did the agent choose to look at first? Why?")
    print(f"  - What did it skip? Would you have skipped the same things?")
    print(f"  - Where did it flag uncertainty? Do you agree?")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
