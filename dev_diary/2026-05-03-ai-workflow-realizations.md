# Dev Diary #2 - AI Workflow Realizations

Date: 2026-05-03  
Project: Dungeon Daddy  
Focus: Workflow Evolution, TDD, and AI Drift

---

## The Honeymoon Phase Ends Quickly

The first few days of Dungeon Daddy were exciting.

The AI could:
- scaffold systems rapidly
- generate tests
- refactor code
- and help design architecture

But very quickly, a more complicated reality emerged.

The issue was not:
> “Can the AI generate code?”

The issue became:
> “Can the AI maintain coherent architectural intent over time?”

That turned out to be much harder.

---

## AI Drift Is Real

As implementation progressed, Claude occasionally began:
- changing architectural approaches
- introducing new abstractions
- adding unnecessary complexity
- or quietly deviating from earlier design decisions

One example involved shifting implementation approaches toward Pydantic-based structures that were not originally part of the intended design.

The AI was not behaving irrationally.

In many cases, the changes were technically reasonable.

But they were not always aligned with:
- the desired simplicity
- the intended architecture
- or the actual scale of the project

This created an important insight:

> AI systems optimize locally unless guided globally.

The human architect remains responsible for maintaining project direction.

---

## The Importance of Small Context Windows

Long conversations produced inconsistent behavior.

As context windows grew:
- architectural consistency weakened
- old assumptions resurfaced
- previously solved issues reappeared
- and implementation drift increased

This led to a major workflow change:
breaking work into smaller, tightly-scoped phases.

The results improved dramatically.

Smaller contexts produced:
- cleaner outputs
- more reliable implementations
- and less architectural confusion

---

## TDD Starts Feeling Necessary

Initially, testing was viewed as helpful.

Now it felt mandatory.

The faster the AI generated code:
- the easier it became to introduce regressions
- the harder it became to manually track correctness
- and the more important behavioral validation became

The workflow evolved into:

1. Define behavior
2. Generate tests
3. Generate implementation
4. Run tests
5. Correct failures
6. Validate manually

This structure stabilized development significantly.

---

## UI Automation Becomes Important

One particularly interesting realization emerged around UI testing.

Claude wanted to validate UI behavior manually through screenshots and application launches.

This led to experimentation with:
- automated Arcade startup/shutdown scripts
- screenshot generation
- and lightweight UI automation

The goal was simple:
allow the AI to observe actual application behavior instead of relying entirely on static code reasoning.

This was surprisingly effective.

---

## AI Coding Feels Less Like Programming and More Like Leadership

An unexpected pattern emerged.

The most valuable human contribution was not typing code.

It was:
- defining goals
- constraining complexity
- clarifying intent
- validating outputs
- and managing system coherence

The role felt increasingly similar to:
- architecture leadership
- technical direction
- and team coordination

Rather than traditional implementation work.

---

## Complexity Still Wins

AI accelerated development speed dramatically.

But it did not eliminate complexity.

In some ways, it increased the need for architectural discipline because:
- implementation became cheap
- experimentation became easy
- and complexity could accumulate faster than before

This created a dangerous temptation:
overbuilding systems simply because the AI could generate them quickly.

That risk became increasingly obvious during Dungeon Daddy development.

---

## Most Important Lesson So Far

The biggest realization at this stage:

> AI-assisted development is not about replacing engineering discipline.
>
> It is about amplifying the consequences of good and bad engineering decisions.

Good architecture becomes incredibly powerful.

Bad architecture becomes incredibly dangerous.