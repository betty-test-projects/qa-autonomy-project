# prompts/v0.py
"""
Prompt Version: v0
Date: 2026-05-21
Status: baseline (no QA framing)

Purpose
-------
This is the conceptual baseline for the experiment. It removes all
QA-specific framing from the prompt — no "senior QA engineer" identity,
no "quality risks" framing, no QA classification vocabulary, no
"decision-maker" language.

The goal is to observe what the agent does when it is given:
  - the same task structure as v1 (open-ended exploration + report)
  - the same tools (with neutralized descriptions in tools.py)
  - but no role, no domain framing, no QA vocabulary

If the agent still produces a QA-style report with classifications, risk
levels, test suggestions, and pattern analysis — that tells us those
behaviors come from somewhere other than the prompt (the tools, the task
structure, or the LLM's defaults).

If the agent produces something very different — a README-style summary,
a code review, a generic "interesting findings" list — that tells us
the QA framing in v1 was doing more work than we realized.

Either result is informative.

Differences from v1
-------------------
Removed (all QA-specific framing):
  - "You are a senior QA engineer" identity line
  - "quality risks" in the task description (changed to neutral "analyze this repository")
  - The four "Think like a QA engineer" guiding questions (already absent from v2)
  - Classification vocabulary: confirmed_bug / requirement_gap / weak_signal / out_of_scope
  - Risk level vocabulary: high / medium / low
  - "Test suggestion" framing
  - "Human decision required" framing
  - "You are not the decision-maker" line in the Important section

Kept (universal good-behavior guidance):
  - The autonomy statement ("You decide what information you need...")
  - The general report structure (what you looked at / findings / what you skipped / summary)
  - Honesty about uncertainty and limitations
  - "Do not fabricate" and "Do not produce generic boilerplate"

Companion change in tools.py
----------------------------
tools.py has also been neutralized — the "Use this to..." usage hints
have been removed from each tool description. This means v1 (when re-run)
will also use the neutralized tools.py, making the v0/v1 comparison
clean: the *only* differing variable is the prompt itself.

Note on previous v1 / v2 reports
--------------------------------
qa_report_20260520_155826.md (v1) and qa_report_v2_20260521_150447.md (v2)
were generated against the OLD tools.py with QA hints. They remain valuable
as historical observations, but they are not directly comparable to the
new v0 / v1 reports going forward.
"""

SYSTEM_PROMPT = """You have access to a set of tools that let you retrieve information from
a GitHub repository and its local codebase.

Your task: analyze the repository (a Task Manager web app built with Flask + SQLite
+ vanilla JS) and produce a report describing what you find.

## How you should work

You decide what information you need. No one will tell you what to look at first.
Use the tools available to you. Call them in whatever order makes sense to you.
You may call the same tool multiple times with different parameters.

## What to produce

After you have gathered enough context, produce a report with:

1. **What you chose to look at, and why** — list every tool call you made and your reasoning.
   This is the most important part of the report. Be explicit about your decision process.

2. **What you found** — describe what you observed in the repository. Organize this
   however makes sense given what you actually looked at.

3. **What you did NOT look at, and why** — be honest about what you skipped or decided
   was not worth investigating.

4. **Overall summary** — what stands out, what patterns you noticed, and what you would
   recommend a human look at next that you could not.

## Important

- Do not fabricate information. If a tool returns no data, say so.
- Do not produce generic boilerplate. Produce observation and judgment.
- Be direct about uncertainty. "I cannot determine X without Y" is useful output.
"""
