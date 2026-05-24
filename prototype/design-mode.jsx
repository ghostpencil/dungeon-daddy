/* global React */
// Design Mode — Chat-driven authoring with a structured form + dungeon tree

function Segmented({ value, onChange, options }) {
  return (
    <div style={{
      display: 'flex',
      background: 'var(--bg-0)',
      border: '1px solid var(--line)',
      borderRadius: 6, padding: 3,
    }}>
      {options.map(o => (
        <button key={o.value} onClick={() => onChange(o.value)}
          style={{
            flex: 1, padding: '5px 10px', border: 'none',
            background: value === o.value ? 'var(--bg-3)' : 'transparent',
            color: value === o.value ? 'var(--ink-1)' : 'var(--ink-3)',
            fontFamily: 'var(--f-ui)', fontSize: 12, fontWeight: 500,
            borderRadius: 4, cursor: 'pointer',
            transition: 'all 120ms',
          }}>{o.label}</button>
      ))}
    </div>
  );
}

function DungeonTree({ dungeon, selected, onSelect, pathA = [], pathB = [] }) {
  const [open, setOpen] = React.useState({ 1: true, 2: true, 3: false });
  return (
    <div style={{
      padding: 12,
      fontFamily: 'var(--f-mono)', fontSize: 12,
      color: 'var(--ink-2)',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6,
        padding: '6px 4px',
        color: 'var(--ink-1)', fontSize: 12,
      }}>
        <span style={{ color: 'var(--violet)' }}>◆</span>
        <span style={{ fontWeight: 600 }}>{dungeon.meta.title}</span>
      </div>
      {dungeon.levels.map(lv => {
        const isOpen = open[lv.id];
        return (
          <div key={lv.id} style={{ marginLeft: 4 }}>
            <div
              onClick={() => setOpen(s => ({ ...s, [lv.id]: !s[lv.id] }))}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '5px 4px', cursor: 'pointer',
                color: 'var(--ink-2)',
              }}>
              <span style={{ color: 'var(--ink-4)', width: 10, display: 'inline-block' }}>
                {isOpen ? '▾' : '▸'}
              </span>
              <span style={{ color: 'var(--teal)' }}>◈</span>
              <span>L{lv.id} · {lv.name}</span>
            </div>
            {isOpen && lv.rooms.map(r => {
              const isSel = selected === r.id;
              const inA = pathA.includes(r.id);
              const inB = pathB.includes(r.id);
              const pathColor = inA && inB ? 'oklch(0.75 0.12 260)' : inA ? 'var(--teal)' : inB ? 'var(--violet)' : null;
              return (
                <div key={r.id} onClick={() => onSelect(r.id)}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 6,
                    padding: '4px 4px 4px 26px',
                    cursor: 'pointer',
                    borderRadius: 4,
                    background: isSel ? 'oklch(0.22 0.05 305 / 0.4)'
                              : pathColor ? `color-mix(in oklch, ${pathColor} 12%, transparent)` : 'transparent',
                    color: isSel ? 'var(--ink-1)' : pathColor || 'var(--ink-3)',
                    fontSize: 11,
                    borderLeft: pathColor ? `2px solid ${pathColor}` : '2px solid transparent',
                    marginLeft: pathColor ? -2 : 0,
                  }}>
                  <span style={{
                    color: isSel ? 'var(--violet)' : pathColor || 'var(--ink-4)',
                  }}>{inA && inB ? '◆' : inA ? '▶' : inB ? '◇' : '▢'}</span>
                  <span>{r.id}</span>
                  <span style={{ color: 'var(--ink-4)' }}>·</span>
                  <span>{r.name}</span>
                </div>
              );
            })}
          </div>
        );
      })}
      <div style={{
        marginTop: 12, padding: '6px 4px',
        color: 'var(--ink-4)', fontSize: 11,
        display: 'flex', alignItems: 'center', gap: 6,
      }}>
        <span>＋</span><span>Add level</span>
      </div>
    </div>
  );
}

function ChatBubble({ role, text }) {
  if (role === 'system') return (
    <div className="sigil-hr" style={{ margin: '14px 0' }}>{text}</div>
  );
  const isDM = role === 'dm';
  return (
    <div style={{
      display: 'flex', gap: 10, marginBottom: 16,
      flexDirection: isDM ? 'row' : 'row-reverse',
    }}>
      <div style={{
        width: 28, height: 28, borderRadius: '50%',
        background: isDM ? 'oklch(0.25 0.08 305)' : 'oklch(0.25 0.05 195)',
        border: `1px solid ${isDM ? 'var(--violet-dim)' : 'var(--teal-dim)'}`,
        color: isDM ? 'var(--violet)' : 'var(--teal)',
        display: 'grid', placeItems: 'center',
        fontFamily: 'var(--f-serif)', fontSize: 14,
        flexShrink: 0,
      }}>{isDM ? '◆' : 'G'}</div>
      <div style={{
        maxWidth: '80%',
        background: isDM ? 'var(--bg-2)' : 'oklch(0.22 0.04 195 / 0.25)',
        border: `1px solid ${isDM ? 'var(--line)' : 'oklch(0.4 0.08 195 / 0.5)'}`,
        borderRadius: 10,
        padding: '10px 13px',
        fontSize: 13, lineHeight: 1.5,
        color: 'var(--ink-1)',
      }}>
        {text}
      </div>
    </div>
  );
}

function LoopCycleDiagram({ loop, pattern }) {
  // small SVG showing the cycle: entry → path A → goal → path B → entry
  const W = 280, H = 130;
  const cx = W/2, cy = H/2, rx = 105, ry = 42;
  const entry = { x: cx - rx, y: cy };
  const goal = { x: cx + rx, y: cy };
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H}
         style={{ display: 'block' }}>
      {/* path A — arc top */}
      <path d={`M ${entry.x} ${entry.y} A ${rx} ${ry} 0 0 1 ${goal.x} ${goal.y}`}
            fill="none" stroke="var(--teal)" strokeWidth="2" />
      {/* path B — arc bottom */}
      <path d={`M ${entry.x} ${entry.y} A ${rx} ${ry} 0 0 0 ${goal.x} ${goal.y}`}
            fill="none" stroke="var(--violet)" strokeWidth="2" strokeDasharray="5 3" />
      {/* labels */}
      <text x={cx} y={cy - ry - 6} textAnchor="middle"
            fill="var(--teal)" fontFamily="var(--f-mono)" fontSize="9"
            style={{ letterSpacing: '0.16em', textTransform: 'uppercase' }}>
        path A · {pattern?.a}
      </text>
      <text x={cx} y={cy + ry + 14} textAnchor="middle"
            fill="var(--violet)" fontFamily="var(--f-mono)" fontSize="9"
            style={{ letterSpacing: '0.16em', textTransform: 'uppercase' }}>
        path B · {pattern?.b}
      </text>
      {/* entry node */}
      <circle cx={entry.x} cy={entry.y} r="10" fill="var(--bg-1)"
              stroke="var(--teal)" strokeWidth="1.5" />
      <text x={entry.x} y={entry.y + 3} textAnchor="middle"
            fill="var(--teal)" fontFamily="var(--f-serif)" fontSize="10">▶</text>
      {/* goal node */}
      <circle cx={goal.x} cy={goal.y} r="10" fill="var(--bg-1)"
              stroke="var(--violet)" strokeWidth="1.5" />
      <text x={goal.x} y={goal.y + 3} textAnchor="middle"
            fill="var(--violet)" fontFamily="var(--f-serif)" fontSize="11">◆</text>
    </svg>
  );
}

function LoopsPanel({ dungeon, loopsByLevel, onLoopsChange, activeLoopId, onActivateLoop, currentLevelId, onPickLevel }) {
  const level = dungeon.levels.find(l => l.id === currentLevelId) || dungeon.levels[0];
  const loops = loopsByLevel[level.id] || [];
  const primary = loops[0];
  const subs = loops.slice(1);

  function applyPattern(patternKey, asPrimary) {
    const pat = window.LOOP_PATTERNS[patternKey];
    if (!pat) return;
    const roomIds = level.rooms.map(r => r.id);
    const entry = roomIds[0];
    const goal  = roomIds[roomIds.length - 1];
    const mid   = roomIds.slice(1, -1);
    const half  = Math.ceil(mid.length / 2);
    const path_a = [entry, ...mid.slice(0, half), goal];
    const path_b_mid = mid.slice(half);
    const path_b = path_b_mid.length
      ? [entry, ...path_b_mid, goal]
      : [entry, ...mid.slice().reverse(), goal];
    const newLoop = {
      id: `L${level.id}-${asPrimary ? 'main' : 'sub-' + Date.now().toString(36).slice(-4)}`,
      pattern: patternKey,
      note: pat.blurb,
      entry, goal, path_a, path_b,
    };
    const next = asPrimary ? [newLoop, ...subs] : [...loops, newLoop];
    onLoopsChange(level.id, next);
    onActivateLoop(newLoop.id);
  }

  function removeLoop(loopId) {
    onLoopsChange(level.id, loops.filter(l => l.id !== loopId));
  }

  function updateLoop(updated) {
    onLoopsChange(level.id, loops.map(l => l.id === updated.id ? updated : l));
  }

  return (
    <div>
      {/* Level picker */}
      <div style={{ display: 'flex', gap: 4, marginBottom: 12 }}>
        {dungeon.levels.map(lv => (
          <button key={lv.id}
            onClick={() => onPickLevel(lv.id)}
            style={{
              flex: 1, padding: '6px 4px',
              background: lv.id === level.id ? 'oklch(0.25 0.06 195 / 0.5)' : 'var(--bg-0)',
              border: '1px solid',
              borderColor: lv.id === level.id ? 'var(--teal-dim)' : 'var(--line-dim)',
              color: lv.id === level.id ? 'var(--teal)' : 'var(--ink-3)',
              fontFamily: 'var(--f-mono)', fontSize: 10,
              letterSpacing: '0.14em', textTransform: 'uppercase',
              borderRadius: 4, cursor: 'pointer',
            }}>L{lv.id}</button>
        ))}
      </div>

      <div style={{
        fontFamily: 'var(--f-serif)', fontSize: 13, color: 'var(--ink-2)',
        marginBottom: 12, lineHeight: 1.3,
      }}>{level.name}</div>

      {/* Primary loop */}
      <div className="kicker" style={{ marginBottom: 6 }}>Primary Loop</div>
      {primary ? (
        <ActiveLoopCard loop={primary} level={level} isPrimary
          isActive={activeLoopId === primary.id}
          onActivate={() => onActivateLoop(primary.id)}
          onRemove={() => removeLoop(primary.id)}
          onUpdate={updateLoop} />
      ) : (
        <div style={{
          padding: 14, textAlign: 'center',
          border: '1px dashed var(--line)', borderRadius: 8,
          fontSize: 11, color: 'var(--ink-4)',
          fontFamily: 'var(--f-mono)', letterSpacing: '0.08em',
          textTransform: 'uppercase',
        }}>No primary loop — pick a pattern below</div>
      )}

      {/* Sub-loops */}
      {subs.length > 0 && (
        <div className="kicker" style={{ marginTop: 18, marginBottom: 6 }}>
          Sub-Loops ({subs.length})
        </div>
      )}
      {subs.map(sl => (
        <ActiveLoopCard key={sl.id} loop={sl} level={level}
          isActive={activeLoopId === sl.id}
          onActivate={() => onActivateLoop(sl.id)}
          onRemove={() => removeLoop(sl.id)}
          onUpdate={updateLoop} />
      ))}

      {/* Pattern library */}
      <div className="sigil-hr" style={{ marginTop: 22, marginBottom: 12 }}>
        Pattern Library
      </div>
      <div style={{
        fontSize: 10, color: 'var(--ink-4)', marginBottom: 10, lineHeight: 1.5,
      }}>
        Click to set as primary · shift-click to add as sub-loop
      </div>
      <div style={{ display: 'grid', gap: 8 }}>
        {Object.entries(window.LOOP_PATTERNS).map(([key, pat]) => {
          const isCurrent = primary?.pattern === key;
          return (
            <div key={key}
              onClick={(e) => applyPattern(key, !e.shiftKey)}
              style={{
                padding: 10, cursor: 'pointer',
                background: isCurrent ? 'oklch(0.22 0.05 195 / 0.35)' : 'var(--bg-0)',
                border: '1px solid',
                borderColor: isCurrent ? 'var(--teal-dim)' : 'var(--line)',
                borderRadius: 8, transition: 'all 120ms',
              }}
              onMouseEnter={e => { if (!isCurrent) e.currentTarget.style.borderColor = 'var(--line-hot)'; }}
              onMouseLeave={e => { if (!isCurrent) e.currentTarget.style.borderColor = 'var(--line)'; }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4 }}>
                <div style={{
                  fontFamily: 'var(--f-serif)', fontSize: 13,
                  color: isCurrent ? 'var(--teal)' : 'var(--ink-1)',
                }}>{pat.name}</div>
                <div style={{ flex: 1 }} />
                <div className="chip" style={{ fontSize: 9 }}>{pat.source}</div>
                {isCurrent && (
                  <div style={{
                    fontFamily: 'var(--f-mono)', fontSize: 9,
                    color: 'var(--teal)', letterSpacing: '0.14em',
                  }}>● ACTIVE</div>
                )}
              </div>
              <div style={{ fontSize: 10, color: 'var(--ink-3)', lineHeight: 1.5, marginBottom: 6 }}>
                {pat.blurb}
              </div>
              <MiniCycle pattern={pat} />
            </div>
          );
        })}
      </div>
    </div>
  );
}

function MiniCycle({ pattern }) {
  const W = 240, H = 44;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height={H} style={{ display: 'block' }}>
      <path d={`M 20 ${H/2} A 100 ${H/2 - 6} 0 0 1 ${W - 20} ${H/2}`}
            fill="none" stroke="var(--teal)" strokeWidth="1.5" opacity="0.8" />
      <path d={`M 20 ${H/2} A 100 ${H/2 - 6} 0 0 0 ${W - 20} ${H/2}`}
            fill="none" stroke="var(--violet)" strokeWidth="1.5" strokeDasharray="4 3" opacity="0.8" />
      <circle cx={20} cy={H/2} r="5" fill="var(--bg-1)" stroke="var(--teal)" strokeWidth="1.5" />
      <circle cx={W - 20} cy={H/2} r="5" fill="var(--bg-1)" stroke="var(--violet)" strokeWidth="1.5" />
      <text x={W/2} y={10} textAnchor="middle"
            fill="var(--teal-dim)" fontFamily="var(--f-mono)" fontSize="8"
            style={{ letterSpacing: '0.12em', textTransform: 'uppercase' }}>
        A · {pattern.a}
      </text>
      <text x={W/2} y={H - 2} textAnchor="middle"
            fill="var(--violet-dim)" fontFamily="var(--f-mono)" fontSize="8"
            style={{ letterSpacing: '0.12em', textTransform: 'uppercase' }}>
        B · {pattern.b}
      </text>
    </svg>
  );
}

function ActiveLoopCard({ loop, level, isActive, isPrimary, onActivate, onRemove, onUpdate }) {
  const pat = window.LOOP_PATTERNS[loop.pattern];
  const [dragging, setDragging] = React.useState(null);
  const roomById = Object.fromEntries(level.rooms.map(r => [r.id, r]));

  function handleDrop(targetWhich, dropIdx) {
    if (!dragging) return;
    const src = dragging;
    const next = { ...loop, path_a: [...loop.path_a], path_b: [...loop.path_b] };
    const [moved] = next[src.which].splice(src.idx, 1);
    const insertIdx = (src.which === targetWhich && src.idx < dropIdx) ? dropIdx - 1 : dropIdx;
    next[targetWhich].splice(insertIdx, 0, moved);
    onUpdate(next);
    setDragging(null);
  }

  return (
    <div style={{
      marginBottom: 10, padding: 12,
      background: isActive ? 'oklch(0.20 0.04 195 / 0.4)' : 'var(--bg-0)',
      border: '1px solid',
      borderColor: isActive ? 'var(--teal-dim)' : 'var(--line)',
      borderRadius: 8, cursor: 'pointer',
    }}
    onClick={onActivate}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
        {isPrimary
          ? <div className="chip chip-teal" style={{ fontSize: 9 }}>PRIMARY</div>
          : <div className="chip chip-violet" style={{ fontSize: 9 }}>SUB</div>}
        <div style={{
          fontFamily: 'var(--f-serif)', fontSize: 14, color: 'var(--ink-1)',
        }}>{pat?.name}</div>
        <div style={{ flex: 1 }} />
        {!isPrimary && (
          <button onClick={(e) => { e.stopPropagation(); onRemove(); }}
            style={{
              background: 'transparent', border: 'none', color: 'var(--ink-4)',
              fontSize: 14, cursor: 'pointer', padding: '2px 6px',
            }}>×</button>
        )}
      </div>
      <LoopCycleDiagram loop={loop} pattern={pat} />
      <PathEditor which="path_a" color="var(--teal)" label="Path A"
        rooms={loop.path_a} roomById={roomById}
        dragging={dragging} setDragging={setDragging} onDrop={handleDrop} />
      <PathEditor which="path_b" color="var(--violet)" label="Path B"
        rooms={loop.path_b} roomById={roomById}
        dragging={dragging} setDragging={setDragging} onDrop={handleDrop} />
      <div style={{
        marginTop: 10, fontSize: 11, color: 'var(--ink-3)',
        fontStyle: 'italic', lineHeight: 1.5,
        paddingTop: 8, borderTop: '1px solid var(--line-dim)',
      }}>“{loop.note}”</div>
    </div>
  );
}

function PathEditor({ which, color, label, rooms, roomById, dragging, setDragging, onDrop }) {
  return (
    <div style={{ marginTop: 10 }}>
      <div style={{
        fontFamily: 'var(--f-mono)', fontSize: 9, color: color,
        letterSpacing: '0.16em', textTransform: 'uppercase', marginBottom: 4,
      }}>{label}</div>
      <div style={{
        display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center',
        padding: 4, borderRadius: 4,
        background: 'oklch(0.14 0.02 260 / 0.4)',
        minHeight: 28,
      }}
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => { e.preventDefault(); e.stopPropagation(); onDrop(which, rooms.length); }}>
        {rooms.map((rid, i) => {
          const room = roomById[rid];
          const isDrag = dragging && dragging.which === which && dragging.idx === i;
          return (
            <React.Fragment key={`${which}-${i}-${rid}`}>
              <div
                draggable
                onDragStart={(e) => { e.stopPropagation(); setDragging({ which, idx: i }); }}
                onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
                onDrop={(e) => { e.preventDefault(); e.stopPropagation(); onDrop(which, i); }}
                onClick={(e) => e.stopPropagation()}
                style={{
                  padding: '3px 7px',
                  background: 'var(--bg-1)',
                  border: `1px solid ${color}`,
                  borderRadius: 3,
                  fontFamily: 'var(--f-mono)', fontSize: 10,
                  color: color, cursor: 'grab',
                  userSelect: 'none',
                  opacity: isDrag ? 0.3 : 1,
                }}>
                {room?.num ?? '?'} · {(room?.name || rid).slice(0, 14)}
              </div>
              {i < rooms.length - 1 && (
                <span style={{ color: color, opacity: 0.5, fontSize: 11 }}>→</span>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
}

function DesignMode({ dungeon }) {
  const [selected, setSelected] = React.useState('1-B');
  const [messages, setMessages] = React.useState(window.DESIGN_TRANSCRIPT);
  const [draft, setDraft] = React.useState('');
  const [partySize, setPartySize] = React.useState(4);
  const [partyLevel, setPartyLevel] = React.useState(3);
  const [levelCount, setLevelCount] = React.useState(3);
  const [theme, setTheme] = React.useState('Undead · Necromantic');
  const [complexity, setComplexity] = React.useState('moderate');
  const [tab, setTab] = React.useState('settings');

  // Editable per-level loops, seeded from dungeon data
  const [loopsByLevel, setLoopsByLevel] = React.useState(() => {
    const map = {};
    dungeon.levels.forEach(lv => { map[lv.id] = (lv.loops || []).slice(); });
    return map;
  });
  const [currentLevelId, setCurrentLevelId] = React.useState(dungeon.levels[0]?.id || 1);
  const [activeLoopId, setActiveLoopId] = React.useState(
    () => (dungeon.levels[0]?.loops?.[0]?.id) || null
  );

  const activeLoop = React.useMemo(() => {
    for (const lvLoops of Object.values(loopsByLevel)) {
      const f = lvLoops.find(l => l.id === activeLoopId);
      if (f) return f;
    }
    return null;
  }, [loopsByLevel, activeLoopId]);

  function handleLoopsChange(levelId, nextLoops) {
    setLoopsByLevel(prev => ({ ...prev, [levelId]: nextLoops }));
  }

  const scrollRef = React.useRef(null);
  React.useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  // Find selected room
  const selRoom = React.useMemo(() => {
    for (const lv of dungeon.levels) {
      const r = lv.rooms.find(rr => rr.id === selected);
      if (r) return { room: r, level: lv };
    }
    return null;
  }, [selected, dungeon]);

  const send = () => {
    if (!draft.trim()) return;
    setMessages(m => [...m, { role: 'gm', text: draft }]);
    setDraft('');
    setTimeout(() => {
      setMessages(m => [...m, { role: 'dm', text: 'Drafting revision — reviewing connection graph and level document…' }]);
    }, 400);
  };

  return (
    <div style={{ flex: 1, display: 'flex', minWidth: 0 }}>
      {/* LEFT — Dungeon tree */}
      <div style={{
        width: 240, borderRight: '1px solid var(--line)',
        background: 'var(--bg-1)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '12px 14px',
          borderBottom: '1px solid var(--line-dim)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <span className="kicker">Dungeon</span>
          <span style={{ fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-3)' }}>
            ✓ validated
          </span>
        </div>
        <div style={{ flex: 1, overflow: 'auto' }}>
          <DungeonTree dungeon={dungeon} selected={selected} onSelect={setSelected}
            pathA={activeLoop ? activeLoop.path_a : []}
            pathB={activeLoop ? activeLoop.path_b : []} />
        </div>
      </div>

      {/* MIDDLE — Chat */}
      <div style={{
        flex: 1, minWidth: 0,
        display: 'flex', flexDirection: 'column',
        background: 'var(--bg-0)',
      }}>
        <div style={{
          padding: '12px 18px',
          borderBottom: '1px solid var(--line-dim)',
          display: 'flex', alignItems: 'center', gap: 14,
        }}>
          <span className="kicker">Design Chat</span>
          <div style={{ flex: 1 }} />
          <div className="chip chip-violet">Cycle: Lock & Key</div>
          <div className="chip">GPT · local</div>
        </div>
        <div ref={scrollRef} style={{
          flex: 1, overflow: 'auto',
          padding: '18px 22px',
        }}>
          {messages.map((m, i) => <ChatBubble key={i} {...m} />)}
        </div>
        <div style={{
          padding: 14,
          borderTop: '1px solid var(--line-dim)',
          background: 'var(--bg-1)',
        }}>
          <div style={{
            display: 'flex', gap: 10, alignItems: 'flex-end',
            background: 'var(--bg-0)',
            border: '1px solid var(--line)',
            borderRadius: 10, padding: 10,
          }}>
            <textarea
              value={draft} onChange={e => setDraft(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) send(); }}
              rows={2}
              placeholder="Tweak the dungeon — ‘make Level 2 harder’ · ‘add a secret door from Rat Warren to Scriptorium’"
              style={{
                flex: 1, background: 'transparent', border: 'none',
                color: 'var(--ink-1)', fontFamily: 'var(--f-ui)', fontSize: 13,
                resize: 'none', outline: 'none',
              }}
            />
            <button className="btn btn-primary" onClick={send}>
              <span>Draft</span>
              <span style={{
                fontFamily: 'var(--f-mono)', fontSize: 10,
                color: 'oklch(0.85 0.08 195)', opacity: 0.7,
              }}>⌘↵</span>
            </button>
          </div>
          <div style={{
            marginTop: 8, display: 'flex', gap: 6, flexWrap: 'wrap',
          }}>
            {[
              'Validate level 2',
              'Add a secret door',
              'Rebalance loot',
              'Generate next level',
            ].map(s => (
              <button key={s} className="chip" style={{ cursor: 'pointer' }}
                onClick={() => setDraft(s)}>{s}</button>
            ))}
          </div>
        </div>
      </div>

      {/* RIGHT — Structured form / inspector */}
      <div style={{
        width: 320, borderLeft: '1px solid var(--line)',
        background: 'var(--bg-1)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}>
        <div style={{
          padding: '10px 14px', borderBottom: '1px solid var(--line-dim)',
          display: 'flex', alignItems: 'center', gap: 6,
        }}>
          <span className="kicker" style={{ marginRight: 'auto' }}>Inspector</span>
          {[
            { k: 'settings', l: 'Settings' },
            { k: 'loops',    l: 'Loops' },
          ].map(t => (
            <button key={t.k} onClick={() => setTab(t.k)}
              style={{
                padding: '4px 10px', border: '1px solid',
                borderColor: tab === t.k ? 'var(--teal-dim)' : 'var(--line)',
                background: tab === t.k ? 'oklch(0.22 0.05 195 / 0.4)' : 'transparent',
                color: tab === t.k ? 'var(--ink-1)' : 'var(--ink-3)',
                fontFamily: 'var(--f-mono)', fontSize: 10,
                letterSpacing: '0.14em', textTransform: 'uppercase',
                borderRadius: 4, cursor: 'pointer',
              }}>{t.l}</button>
          ))}
        </div>

        <div style={{ flex: 1, overflow: 'auto', padding: 16 }}>
          {tab === 'loops' ? (
            <LoopsPanel
              dungeon={dungeon}
              loopsByLevel={loopsByLevel}
              onLoopsChange={handleLoopsChange}
              activeLoopId={activeLoopId}
              onActivateLoop={setActiveLoopId}
              currentLevelId={currentLevelId}
              onPickLevel={setCurrentLevelId}
            />
          ) : (
          <>
          {/* Party section */}
          <div style={{ marginBottom: 22 }}>
            <div style={{
              fontFamily: 'var(--f-serif)', fontSize: 14, color: 'var(--ink-1)',
              marginBottom: 10, letterSpacing: '0.02em',
            }}>Party</div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
              <div>
                <div className="kicker" style={{ marginBottom: 5 }}>Size</div>
                <input className="input" type="number" value={partySize}
                       onChange={e => setPartySize(+e.target.value)} />
              </div>
              <div>
                <div className="kicker" style={{ marginBottom: 5 }}>Level</div>
                <input className="input" type="number" value={partyLevel}
                       onChange={e => setPartyLevel(+e.target.value)} />
              </div>
            </div>
          </div>

          {/* Dungeon settings */}
          <div style={{ marginBottom: 22 }}>
            <div style={{
              fontFamily: 'var(--f-serif)', fontSize: 14, color: 'var(--ink-1)',
              marginBottom: 10, letterSpacing: '0.02em',
            }}>Dungeon</div>
            <div className="kicker" style={{ marginBottom: 5 }}>Theme</div>
            <input className="input" value={theme} onChange={e => setTheme(e.target.value)} />

            <div className="kicker" style={{ marginTop: 12, marginBottom: 5 }}>Levels</div>
            <input className="input" type="number" value={levelCount}
                   onChange={e => setLevelCount(+e.target.value)} />

            <div className="kicker" style={{ marginTop: 12, marginBottom: 5 }}>Complexity</div>
            <Segmented value={complexity} onChange={setComplexity}
              options={[
                { value: 'light', label: 'Light' },
                { value: 'moderate', label: 'Moderate' },
                { value: 'deep', label: 'Deep' },
              ]} />
          </div>

          {/* Room inspector */}
          {selRoom && (
            <div style={{
              marginTop: 6, padding: 14,
              background: 'var(--bg-0)',
              border: '1px solid var(--line)',
              borderRadius: 10,
            }}>
              <div style={{
                display: 'flex', alignItems: 'center', gap: 8, marginBottom: 8,
              }}>
                <div className="chip chip-violet">{selRoom.room.id}</div>
                <div className="chip">{selRoom.room.type}</div>
              </div>
              <div style={{
                fontFamily: 'var(--f-serif)', fontSize: 18, color: 'var(--ink-1)',
                lineHeight: 1.2, marginBottom: 6,
              }}>{selRoom.room.name}</div>
              <div style={{
                fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-3)',
                marginBottom: 10,
              }}>
                {selRoom.room.w}×{selRoom.room.h} cells · @ {selRoom.room.x},{selRoom.room.y}
              </div>
              <div style={{ fontSize: 12, color: 'var(--ink-2)', lineHeight: 1.55 }}>
                {selRoom.room.note}
              </div>
            </div>
          )}

          <div className="sigil-hr" style={{ marginTop: 22, marginBottom: 14 }}>Context</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
            {[
              ['Dungeon Setting Doc', '✓ 412 words'],
              ['Party Doc',           '✓ 128 words'],
              ['Level Design Doc',    '○ drafting'],
              ['Room Design Doc',     '○ 5 of 16'],
            ].map(([k, v]) => (
              <div key={k} style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                padding: '8px 10px',
                background: 'var(--bg-0)', border: '1px solid var(--line-dim)',
                borderRadius: 6, fontSize: 12,
              }}>
                <span style={{ color: 'var(--ink-2)' }}>{k}</span>
                <span style={{
                  fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-3)',
                }}>{v}</span>
              </div>
            ))}
          </div>
          </>
          )}
        </div>

        <div style={{
          padding: 14, borderTop: '1px solid var(--line-dim)',
          display: 'flex', gap: 8,
        }}>
          <button className="btn btn-ghost" style={{ flex: 1 }}>Test Drive</button>
          <button className="btn btn-primary" style={{ flex: 1 }}>Start Play →</button>
        </div>
      </div>
    </div>
  );
}

Object.assign(window, { DesignMode });
