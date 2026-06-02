# RPG System Specification

## Goal

Create a lightweight narrative RPG system for Dungeon Daddy that supports:

- player character stats
- NPC and monster stats
- actions and abilities
- health as stress tracks
- narrative combat
- investigation
- social scenes
- emotional consequences
- dungeon influence

## Non-goals

Do not build:

- D&D-style tactical combat
- initiative order
- grid movement
- armor class
- damage dice catalogs
- challenge rating
- large class/playbook system
- level-up trees
- item rarity systems

These can be considered later only if playtests prove they are needed.

## Core action roll

Use a Charge-style d6 pool.

Roll a pool of d6s and take the highest die.

| Highest die | Result |
|---|---|
| 1–3 | Bad outcome, failure, or hard consequence |
| 4–5 | Success with consequence |
| 6 | Success |
| multiple 6s | Critical success or enhanced effect |

The roll should answer:

- Do you get what you want?
- What does it cost?
- What changes in the fiction?
- Does the dungeon learn something about you?

## Action list

| Action | Use |
|---|---|
| Fight | Harm, restrain, overpower, duel, defend directly |
| Move | Sneak, climb, dodge, flee, traverse danger |
| Tinker | Repair, disable, craft, manipulate mechanisms |
| Study | Investigate, research, interpret clues, analyze |
| Focus | Resist fear, exert will, perform discipline |
| Sway | Persuade, comfort, deceive, provoke, command socially |
| Sense | Read emotions, notice danger, perceive hidden things |
| Channel | Interact with magic, visions, spirits, dungeon resonance |
| Endure | Withstand pain, exhaustion, poison, pressure |

## Momentum

Momentum is a lightweight player resource.

Initial first-pass rules:

- Characters may gain momentum from strong successes, useful positioning, good roleplay hooks, or abilities.
- Characters may spend momentum to add dice, improve effect, resist consequences, or activate abilities.
- Momentum must be capped to avoid hoarding. Recommended first-pass cap: 6.

## Stress tracks

PCs have four tracks:

| Track | Meaning |
|---|---|
| Body | Physical harm, exhaustion, poison, injury |
| Composure | Fear, panic, shame, grief, despair |
| Bonds | Relationship damage, isolation, distrust, dependency |
| Weird | Occult contamination, memory bleed, dream intrusion, dungeon influence |

Recommended first-pass max: 4 each.

When a track fills, evaluate fallout.

## Clocks

Use clocks for:

- investigations
- combat objectives
- environmental threats
- monster resistance
- boss phases
- dungeon influence
- escape pressure

Clock sizes:

| Clock size | Use |
|---|---|
| 3 | Simple obstacle or weak monster |
| 4 | Standard obstacle |
| 6 | Major obstacle or dangerous monster |
| 8 | Boss phase or major ritual |
| Linked clocks | Multi-stage boss, complex investigation, major dungeon event |

## NPCs and monsters

NPCs and monsters are lightweight.

They should not require full character sheets unless they are major recurring characters.

Minimal monster model:

```text
Name
Type
Threat role
Resistance/threat clock
Instinct
Actions
Special abilities
Stress it inflicts
Fallout tendencies
Tags
Markdown profile
```

## Abilities

Abilities are small rule exceptions that reinforce identity.

Examples:

- gain momentum under a specific fictional trigger
- reduce a specific kind of stress once per scene
- ask an extra question on a successful Study roll
- convert Body stress into clock progress when protecting someone
- accept Weird stress for insight

Abilities should interact with:

- momentum
- stress
- clocks
- fallout
- tags
- memory

## Recovery

Recovery should be fiction-first.

Recovery may clear stress but should require a narrative action:

- rest in a safe room
- receive care
- repair trust
- confess a fear
- reject the dungeon's comfort
- accept the dungeon's comfort at a cost

Recovery from Weird stress should rarely be clean. It should often create memory, dungeon influence, or intimacy risk.

