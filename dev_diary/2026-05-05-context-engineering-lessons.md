# Dev Diary #3 - Context Engineering Lessons

Date: 2026-05-05  
Project: Dungeon Daddy  
Focus: Token Management, Context Collapse, and Workflow Optimization

---

## The First Real Wall

After several successful implementation phases, development hit its first major operational wall:
token exhaustion and context inefficiency.

At first, things felt smooth.
The phased approach was working.
Claude was generating reasonable implementations.
TDD workflows were improving reliability.

But eventually the sessions became unstable.

The problem was not coding capability.

The problem was context management.

---

## The Claude.md Problem

One of the first discoveries involved the `claude.md` file.

Initially, the file instructed Claude to:
- read every specification file
- during every interaction
- regardless of task scope

This turned out to be extremely inefficient.

The consequences:
- massive token consumption
- slower reasoning
- unnecessary context loading
- and increased architectural drift

The AI was spending too much effort re-processing information that was not relevant to the current task.

---

## First Optimization Pass

The workflow was redesigned around:
on-demand specification loading.

The updated approach:
- only load specs relevant to the current task
- reduce unnecessary context reads
- keep implementation scope narrow
- maintain tighter conversational focus

The testing workflow was also updated to formally require TDD behavior instead of relying on prompting reminders.

This immediately improved stability and token efficiency.

---

## Temporary Improvement

For a while, the changes worked well.

Development stabilized.
Implementation quality improved.
Token usage dropped noticeably.

But eventually another problem emerged.

---

## The Realization: AI Sessions Accumulate Entropy

Even with modularized specifications, the AI still had to:
- inspect multiple files
- reconstruct project state
- determine task relevance
- and infer implementation sequence

The issue was subtle but important.

The AI had access to the information...
but not enough guidance about:
- when files mattered
- why they mattered
- and what the current development focus actually was

This created unnecessary reasoning overhead.

---

## Solution #1 - The PROJECT_INDEX File

A major workflow breakthrough came from introducing a `PROJECT_INDEX` file.

The purpose of this file was simple:
provide Claude with a high-level operational roadmap.

The `PROJECT_INDEX` contained:
- the current development phase
- implementation priorities
- relevant specification references
- detailed next steps
- and instructions about which files should be consulted

This dramatically reduced context thrashing.

Instead of reconstructing project state from scattered files, Claude now had:
- a centralized operational guide
- a current-phase roadmap
- and clearer task boundaries

This was one of the most impactful workflow improvements so far.

---

## The UI Testing Problem

Another major issue emerged around UI testing.

Each development phase required the AI to:
- launch Arcade
- wait for startup
- take screenshots
- stop the application
- and validate behavior

Because reusable tooling had not been created early enough, Claude repeatedly attempted to recreate these workflows from scratch.

This produced absurd inefficiencies.

Simple tasks occasionally consumed thousands of tokens because the AI was:
- reinventing harness logic
- debugging automation repeatedly
- or creating entirely new approaches for already-solved problems

This became a painful but valuable lesson.

---

## Solution #2 - Reusable Tooling

The solution was straightforward:
extract reusable functionality into dedicated tools.

A clean session was started.
Claude analyzed prior test scripts.
Common functionality was extracted into reusable utilities.

Eventually this evolved into:
- a reusable Python UI test harness
- standardized startup/shutdown workflows
- screenshot automation
- and documented operational instructions

Instructions for using these tools were added directly into `claude.md`.

The difference was enormous.

This reduced:
- token waste
- duplicated reasoning
- and repeated implementation effort

It also made testing dramatically more reliable.

---

## User Skill Matters More Than Expected

One of the most important realizations had nothing to do with Claude itself.

It involved operator behavior.

At several points, development sessions became bloated because too many unrelated tasks were attempted within the same context window.

This created:
- noisy sessions
- degraded reasoning
- reduced implementation quality
- and expensive debugging/refactoring loops

A critical lesson emerged:

> Long-running AI sessions accumulate cognitive debris.

Eventually the session itself becomes part of the problem.

---

## Solution #3 - Aggressive Context Resetting

The workflow evolved again.

New rules emerged:
- use `/clear` aggressively
- restart sessions frequently
- record next steps before clearing
- use `PROJECT_INDEX` as the recovery anchor
- force clean state reloads when reasoning quality drops

This became one of the most important operational habits in the project.

The practical realization:

> Context persistence is not always an advantage.
>
> Sometimes clean state is far more valuable.

---

## Emerging Understanding

At this stage, Dungeon Daddy no longer felt like:
> “using an AI coding assistant.”

It increasingly felt like:
> designing a development operating system for AI-assisted engineering.

The challenge was not simply generating code.

The challenge was controlling:
- context
- complexity
- drift
- validation
- and operational cost

---

## Most Important Lessons So Far

### Lesson 1
Context is a finite engineering resource.

---

### Lesson 2
AI systems require operational structure to remain efficient over time.

---

### Lesson 3
Reusable tooling is critical in AI-assisted workflows.

Otherwise the AI repeatedly reinvents solved problems.

---

### Lesson 4
Session hygiene matters enormously.

Poor context discipline creates exponential inefficiency.

---

### Lesson 5
The human operator is part of the system architecture.

The quality of the workflow depends heavily on:
- planning discipline
- scope management
- and operational consistency

---

## Final Thoughts

This phase fundamentally changed how Dungeon Daddy development was approached.

The biggest realization:

> Successful AI-assisted development is not just about prompting well.
>
> It is about designing sustainable systems for context management and validation.

That realization may ultimately matter more than the code itself.