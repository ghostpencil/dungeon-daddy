# Dev Diary #4 - UI Automation and Reality

Date: 2026-05-08  
Project: Dungeon Daddy  
Focus: UI Automation, Computer Control, and the Limits of Automated Validation

---

## The Project Finally Starts Feeling Real

After several rounds of workflow improvements, context optimizations, and tooling cleanup, development finally stabilized.

Claude and I pushed all the way through Phase 7.

For the first time, Dungeon Daddy started feeling like:
- a functioning application
- a coherent system
- and not just an experimental prototype

The architecture was cleaner.
Testing workflows were improving.
The phased approach was working.

But one major issue remained:
user interaction.

The game still required manual input to progress through important flows.

That meant one thing:
I needed better UI automation.

---

## The Computer Control Experiment

I discovered a Computer Control MCP service for Claude.

I installed it specifically for Dungeon Daddy.

Honestly, this felt dangerous.

Giving an AI direct control over:
- keyboard input
- mouse input
- application interaction
- and UI workflows

crosses into territory that feels fundamentally different from normal coding assistance.

But despite the risks, it was also the most straightforward solution for automated UI validation.

The alternative would have required building significantly more custom infrastructure.

So I proceeded carefully.

---

## The First Major UI Testing Failure

At first, the automated tests looked promising.

Phase 7 passed automated checks.

But when I manually reviewed the application, serious issues appeared immediately.

The automated UI tests were producing false confidence.

Two major problems emerged:

### Problem 1 - Interaction Validation Was Weak

The UI automation was performing clicks...
but not truly validating the results of those clicks.

The automation could:
- execute actions
- navigate flows
- and continue execution

without properly confirming:
- state transitions
- visual correctness
- or behavioral outcomes

This was an important realization:

> Automated interaction is not the same thing as automated verification.

The AI could “use” the application while still misunderstanding whether the application behaved correctly.

---

### Problem 2 - The UI Broke Under Real Usage

Another issue emerged immediately:
window resizing.

The application technically functioned...
but resizing the screen made the map effectively unusable.

This exposed a major UX problem:
the lack of a proper pan-and-scan system.

The automated tests had completely missed this.

---

## The Pan & Scan Decision

At first, I considered implementing the feature directly within the existing workflow.

But the feature quickly revealed itself to be:
- larger
- more architectural
- and more behaviorally complex

than expected.

So I made a deliberate decision:
create a completely separate specification document dedicated solely to Pan & Scan.

This turned out to be extremely important.

The document became:
- a behavioral contract
- a design clarification tool
- and a planning workspace

before implementation even began.

---

## A Brutal Lesson About AI Planning

I learned an expensive lesson during this phase.

Initially, I asked Claude to:
- think deeply
- plan extensively
- and reason about Pan & Scan

without requiring it to explicitly write its implementation plan incrementally.

This was a mistake.

Within minutes:
- token consumption exploded
- reasoning became increasingly diffuse
- and an enormous amount of context was burned on internal planning loops

In roughly five minutes, Claude consumed an enormous portion of the available token budget.

The session effectively collapsed.

This was one of the clearest demonstrations yet that:
unbounded AI reasoning can become catastrophically inefficient.

---

## New Rule - Force Externalized Planning

A major workflow rule emerged from this failure:

> Make the AI write the plan incrementally.

Do not allow large hidden reasoning spirals.

Instead:
- force visible planning steps
- review direction frequently
- constrain scope aggressively
- and validate assumptions early

This dramatically improved:
- token efficiency
- implementation clarity
- and architectural control

---

## Fixing the UI Automation Workflow

The next improvement involved refining the UI testing methodology itself.

The core issue:
Claude was not consistently verifying state changes after UI interactions.

The solution was straightforward but important:
require screenshots after every meaningful UI action.

The updated workflow became:

1. Perform interaction
2. Capture screenshot
3. Verify visual result
4. Continue only after validation

This significantly improved reliability.

The AI now had:
- visible evidence of state transitions
- better behavioral awareness
- and more trustworthy UI validation loops

---

## A Bigger Realization About AI Testing

This phase revealed something extremely important.

AI-generated tests can absolutely miss real-world usability problems.

The automated tests:
- passed
- executed correctly
- and appeared successful

while the actual application still had major UX flaws.

That realization matters enormously.

Because it highlights a dangerous possibility:

> AI systems can create the illusion of quality if validation targets are incomplete.

The tests were technically correct.
But they were validating the wrong things.

---

## The Human Role Remains Critical

This phase reinforced a growing belief:

The human engineer is still responsible for:
- defining meaningful validation
- understanding user experience
- detecting architectural weakness
- and identifying missing behavioral requirements

The AI can execute workflows rapidly.

But determining whether those workflows matter...
still requires human judgment.

---

## Most Important Lessons So Far

### Lesson 1
Automated execution is not automated understanding.

---

### Lesson 2
AI planning must be constrained and externalized.

---

### Lesson 3
Large hidden reasoning loops are operationally dangerous.

---

### Lesson 4
Behavioral validation matters more than technical completion.

---

### Lesson 5
UI automation requires state verification, not just interaction simulation.

---

## Final Thoughts

This phase changed how I think about AI-assisted testing.

Initially, I assumed:
> better automation equals better validation.

Now I believe something more nuanced:

> Better validation design equals better validation.

The distinction matters.

A lot.