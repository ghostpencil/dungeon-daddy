// ─────────────────────────────────────────────────────────────
// Sample dungeon: Tomb of the Forgotten King
// 3 levels, hand-crafted data that renders as a grid (Arcade 2D friendly)
// ─────────────────────────────────────────────────────────────

// ─────────────────────────────────────────────────────────────
// Loop pattern catalog — adapted from:
//   • Dormans, "Cyclic Dungeon Generation" (Unexplored, 2017)
//   • Sersa Victory, "Cyclic Dungeon Generation" (TTRPG adaptation)
//   • The Alexandrian, "Xandering the Dungeon" parts 1–5
// Each loop: entry → path_a → goal → path_b → entry. Short/long determines
// where the tension lives. These are the only generator primitives we use.
// ─────────────────────────────────────────────────────────────
window.LOOP_PATTERNS = {
  lock_key: {
    name: "Lock & Key",
    blurb: "Path A short to a locked door. Path B long — ends at the key, loops back near the lock.",
    a: "short", b: "long",
    beats: ["entry", "locked door (goal)", "key revealed", "back near lock"],
    source: "Dormans"
  },
  gambit: {
    name: "Gambit",
    blurb: "Path A presents a risk or temptation; B is the safe long way. Both converge at the prize.",
    a: "short", b: "long",
    beats: ["entry", "temptation / danger", "prize (goal)", "safe return"],
    source: "Dormans"
  },
  foreshadow: {
    name: "Foreshadowing",
    blurb: "Path A teases the goal (seen, not reached). Path B is the real trial to earn it.",
    a: "short", b: "long",
    beats: ["entry", "goal teased", "trial", "goal reached"],
    source: "Sersa Victory"
  },
  fork_choice: {
    name: "True Fork",
    blurb: "Two meaningful paths of equal weight; both reach the goal with different costs.",
    a: "equal", b: "equal",
    beats: ["entry", "divergent trial A", "goal", "divergent trial B"],
    source: "Dormans"
  },
  pursuit: {
    name: "Pursuit",
    blurb: "A waking threat follows path A; players race down B before it catches them.",
    a: "equal", b: "equal",
    beats: ["entry", "trigger / awaken", "chase", "barricade & goal"],
    source: "Sersa Victory"
  },
  secret_shortcut: {
    name: "Secret Shortcut",
    blurb: "Long forward path, hidden return that collapses travel — rewards curiosity (Xandering).",
    a: "long", b: "short (secret)",
    beats: ["entry", "long crawl", "goal", "hidden shortcut"],
    source: "Alexandrian"
  },
  hub_spoke: {
    name: "Hub & Spoke",
    blurb: "Central chamber. Path A collects from spoke rooms; Path B is the revealed descent.",
    a: "long", b: "short",
    beats: ["entry hub", "spoke trials", "hub again", "descent"],
    source: "Alexandrian"
  },
  bottleneck: {
    name: "Branch & Bottleneck",
    blurb: "Paths diverge, then squeeze through a single guarded chokepoint before the goal.",
    a: "equal", b: "equal",
    beats: ["entry", "branch trial", "bottleneck", "goal"],
    source: "Dormans"
  },
  shortcut_back: {
    name: "Shortcut Back",
    blurb: "Forward path is linear; after the goal, a one-way shortcut opens to entry — pacing relief.",
    a: "long", b: "short (one-way)",
    beats: ["entry", "forward crawl", "goal", "shortcut back"],
    source: "Alexandrian"
  }
};

window.DUNGEON = {
  meta: {
    title: "Tomb of the Forgotten King",
    theme: "Undead • Necromantic",
    setting: "A sunken basalt ziggurat on the black coast of Myrr, sealed for 400 years after its king rose as a lich.",
    party: "4 adventurers • level 3 • mixed",
    quest: "Recover the Sundered Crown before the new moon, when the lich re-awakens."
  },
  levels: [
    {
      id: 1,
      name: "The Sunken Vestibule",
      summary: "Waterlogged antechambers, bat-haunted. Cultists left recent footprints.",
      ecology: "Giant rats, stirges, 2 ghoul scouts",
      loop: "Cycle of offerings — a broken ritual that can be completed for passage",
      loops: [
        { id: "L1-main", pattern: "lock_key",
          note: "Shrine is sigil-locked. Key (a shard of bone) is in the Rat Warren.",
          entry: "1-A", goal: "1-B",
          path_a: ["1-A", "1-B"],
          path_b: ["1-A", "1-C", "1-E", "1-D", "1-B"] }
      ],
      width: 16, height: 12,
      entries: [{ x: 0, y: 5, type: "stair_up", label: "Entrance" }],
      rooms: [
        { id: "1-A", num: 1, name: "Flooded Entry",    x: 1,  y: 4, w: 3, h: 3, type: "hall",    note: "Ankle-deep brine. Sconces drip with tar." },
        { id: "1-B", num: 2, name: "Drowned Shrine",   x: 5,  y: 2, w: 4, h: 4, type: "shrine",  note: "Altar of Mythrax. Silver dust on the floor." },
        { id: "1-C", num: 3, name: "Rat Warren",       x: 5,  y: 8, w: 3, h: 3, type: "lair",    note: "Nesting ground. Tight squeeze." },
        { id: "1-D", num: 4, name: "Collapsed Gallery",x: 10, y: 3, w: 4, h: 3, type: "hall",    note: "Murals of the King's coronation, half-eroded." },
        { id: "1-E", num: 5, name: "Descent Chamber",  x: 11, y: 7, w: 3, h: 4, type: "stair",   note: "Spiral stair bored through basalt." }
      ],
      connections: [
        { from: "1-A", to: "1-B", type: "door" },
        { from: "1-A", to: "1-C", type: "hall" },
        { from: "1-B", to: "1-D", type: "door" },
        { from: "1-C", to: "1-E", type: "hole",  note: "Rat tunnel, squeeze DC 12" },
        { from: "1-D", to: "1-E", type: "arch" },
        { from: "1-E", to: "2-A", type: "stair_down" }
      ]
    },
    {
      id: 2,
      name: "Hall of Bound Servants",
      summary: "Stone servants still at their posts. Something bound them — and still watches.",
      ecology: "Bound skeletons, a wraith-steward, 1 mimic disguised as reliquary",
      loop: "Each room honored — bow at each post to pass unharmed",
      loops: [
        { id: "L2-main", pattern: "gambit",
          note: "Reliquary (A) is the tempting shortcut but the mimic guards it. Scriptorium (B) is the long honorable route.",
          entry: "2-A", goal: "2-E",
          path_a: ["2-A", "2-C", "2-E"],
          path_b: ["2-A", "2-B", "2-D", "2-E"] },
        { id: "L2-sub", pattern: "secret_shortcut",
          note: "A collapsed air-shaft from Scriptorium drops into Sealed Descent — bypasses the steward's signet.",
          entry: "2-D", goal: "2-F",
          path_a: ["2-D", "2-E", "2-F"],
          path_b: ["2-D", "2-F"] }
      ],
      width: 18, height: 14,
      entries: [{ x: 9, y: 0, type: "stair_up", label: "From L1" }],
      rooms: [
        { id: "2-A", num: 1, name: "Stair Landing",    x: 8,  y: 1, w: 3, h: 3, type: "stair",  note: "Iron braziers still lit with cold blue flame." },
        { id: "2-B", num: 2, name: "Servants' Hall",   x: 2,  y: 5, w: 6, h: 4, type: "hall",   note: "Twelve skeletons, standing, ceremonial posture." },
        { id: "2-C", num: 3, name: "Reliquary",        x: 12, y: 4, w: 4, h: 4, type: "vault",  note: "Reliquary is a mimic. DC 15 insight." },
        { id: "2-D", num: 4, name: "Scriptorium",      x: 3,  y: 10, w: 5, h: 3, type: "study", note: "Books bound in human skin, still writing themselves." },
        { id: "2-E", num: 5, name: "Wraith's Study",   x: 11, y: 9, w: 4, h: 4, type: "boss",   note: "The Wraith-Steward. Negotiate or fight." },
        { id: "2-F", num: 6, name: "Sealed Descent",   x: 16, y: 11, w: 2, h: 2, type: "stair", note: "Door keyed to the steward's signet." }
      ],
      connections: [
        { from: "2-A", to: "2-B", type: "arch" },
        { from: "2-A", to: "2-C", type: "door" },
        { from: "2-B", to: "2-D", type: "door" },
        { from: "2-C", to: "2-E", type: "door", note: "Sigil-locked" },
        { from: "2-D", to: "2-E", type: "hall" },
        { from: "2-E", to: "2-F", type: "door" },
        { from: "2-F", to: "3-A", type: "stair_down" }
      ]
    },
    {
      id: 3,
      name: "The King's Tomb",
      summary: "The lich-king's resting chamber. The Sundered Crown lies on his brow.",
      ecology: "Lich (sleeping), 2 bone golems, 1 spectral advisor",
      loop: "Sever the three tethers — advisor, golems, throne — before the moon rises",
      loops: [
        { id: "L3-main", pattern: "foreshadow",
          note: "Processional teases the throne through veils. Real path earns the binding through advisor + golems.",
          entry: "3-A", goal: "3-E",
          path_a: ["3-A", "3-B", "3-D", "3-E"],
          path_b: ["3-A", "3-C", "3-D", "3-E"] },
        { id: "L3-pursuit", pattern: "pursuit",
          note: "Once the throne is approached, the lich wakes — golems hunt backward down path A.",
          entry: "3-E", goal: "3-A",
          path_a: ["3-E", "3-D", "3-C", "3-A"],
          path_b: ["3-E", "3-D", "3-B", "3-A"] }
      ],
      width: 20, height: 16,
      entries: [{ x: 0, y: 8, type: "stair_up", label: "From L2" }],
      rooms: [
        { id: "3-A", num: 1, name: "Ossuary Approach", x: 1,  y: 7, w: 4, h: 3, type: "hall",   note: "Walls of stacked skulls, whispering." },
        { id: "3-B", num: 2, name: "Advisor's Nook",   x: 6,  y: 3, w: 4, h: 3, type: "study",  note: "Spectral Advisor. Knows a way to bind the lich." },
        { id: "3-C", num: 3, name: "Golem Forge",      x: 6,  y: 10, w: 4, h: 4, type: "lair",  note: "2 bone golems. Forge still hot." },
        { id: "3-D", num: 4, name: "Processional",     x: 11, y: 6, w: 5, h: 4, type: "hall",   note: "Mile-long audience hall compressed into 25 feet." },
        { id: "3-E", num: 5, name: "Throne of Bone",   x: 16, y: 6, w: 4, h: 4, type: "boss",   note: "The lich-king, crown upon brow. Climax." }
      ],
      connections: [
        { from: "3-A", to: "3-B", type: "arch" },
        { from: "3-A", to: "3-C", type: "door" },
        { from: "3-B", to: "3-D", type: "door" },
        { from: "3-C", to: "3-D", type: "hall" },
        { from: "3-D", to: "3-E", type: "arch", note: "Threshold of binding" }
      ]
    }
  ]
};

// Initial chat transcript — shown in Play mode
window.PLAY_TRANSCRIPT = [
  { role: "system", text: "Tomb of the Forgotten King • Session begins" },
  { role: "gm", text: "The party stands at the Flooded Entry." },
  { role: "dm", text: "The cold brine laps at your boots. Three tar-sconces sputter along the basalt walls, each carved with the crowned-skull sigil of the Forgotten King. A low archway leads west into the Drowned Shrine; you hear skittering to the south." },
  { role: "gm", text: "Aranth checks the sconces for traps." },
  { role: "dm", text: "Roll Investigation. The sconces are fed by a single tar-line in the ceiling — pulling one douses all three. No trap, but whoever posted them wanted the room dark on command." }
];

// Design mode chat — authoring transcript
window.DESIGN_TRANSCRIPT = [
  { role: "dm", text: "Hello, Game Master. Tell me the shape of your dungeon — setting, theme, party. I'll draft a level and you'll approve before I draft the next." },
  { role: "gm", text: "A sunken basalt ziggurat. Lich-king rises on the new moon. 4 adventurers, level 3." },
  { role: "dm", text: "Noted. I'm drafting Level 1 — The Sunken Vestibule. Waterlogged antechambers, a cycle of offerings as the dungeon loop. Five rooms: entry, shrine, rat warren, gallery, descent. Reviewing map now." },
  { role: "dm", text: "✓ Level 1 validated. pytiled-parser OK. Traversable from entry to descent. Want to approve and draft Level 2?" }
];
