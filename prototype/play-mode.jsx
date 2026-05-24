/* global React, MapViewer */
// Play Mode — GM runs a session. Chat on left, map viewer on right.

function PlayBubble({ role, text }) {
  if (role === 'system') {
    return (
      <div className="sigil-hr" style={{ margin: '10px 0' }}>{text}</div>
    );
  }
  const styles = {
    gm: {
      label: 'GM',
      bg: 'transparent',
      color: 'var(--ink-3)',
      accent: 'var(--teal)',
      border: '1px dashed oklch(0.35 0.04 195)',
    },
    dm: {
      label: '◆ Dungeon',
      bg: 'var(--bg-2)',
      color: 'var(--ink-1)',
      accent: 'var(--violet)',
      border: '1px solid var(--line)',
    },
  }[role];

  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{
        fontFamily: 'var(--f-mono)', fontSize: 9,
        letterSpacing: '0.18em', textTransform: 'uppercase',
        color: styles.accent, marginBottom: 5,
      }}>{styles.label}</div>
      <div style={{
        padding: '10px 13px',
        background: styles.bg,
        border: styles.border,
        borderRadius: 8,
        color: styles.color,
        fontSize: 13, lineHeight: 1.6,
        fontFamily: role === 'dm' ? 'var(--f-serif)' : 'var(--f-ui)',
        fontStyle: role === 'gm' ? 'italic' : 'normal',
      }}>{text}</div>
    </div>
  );
}

function LevelStepper({ dungeon, levelIdx, onLevelIdx }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      gap: 3, alignItems: 'center',
    }}>
      <button onClick={() => onLevelIdx(Math.max(0, levelIdx - 1))}
        disabled={levelIdx === 0}
        style={{
          border: '1px solid var(--line)',
          background: 'var(--bg-2)', color: 'var(--ink-2)',
          width: 32, height: 24, borderRadius: 4, cursor: 'pointer',
          opacity: levelIdx === 0 ? 0.4 : 1,
        }}>▲</button>
      <div style={{
        fontFamily: 'var(--f-mono)', fontSize: 10,
        color: 'var(--teal)',
        padding: '4px 0',
        letterSpacing: '0.1em',
      }}>L{dungeon.levels[levelIdx].id}</div>
      <button onClick={() => onLevelIdx(Math.min(dungeon.levels.length - 1, levelIdx + 1))}
        disabled={levelIdx === dungeon.levels.length - 1}
        style={{
          border: '1px solid var(--line)',
          background: 'var(--bg-2)', color: 'var(--ink-2)',
          width: 32, height: 24, borderRadius: 4, cursor: 'pointer',
          opacity: levelIdx === dungeon.levels.length - 1 ? 0.4 : 1,
        }}>▼</button>
    </div>
  );
}

function PlayMode({ dungeon, mapVariant, onMapVariant }) {
  const [levelIdx, setLevelIdx] = React.useState(0);
  const [currentRoom, setCurrentRoom] = React.useState('1-A');
  const [visited, setVisited] = React.useState(new Set(['1-A', '1-B']));
  const [messages, setMessages] = React.useState(window.PLAY_TRANSCRIPT);
  const [draft, setDraft] = React.useState('');
  const [activeLoop, setActiveLoop] = React.useState(null);
  const scrollRef = React.useRef(null);

  const level = dungeon.levels[levelIdx];
  React.useEffect(() => { setActiveLoop(null); }, [levelIdx]);
  const room = level.rooms.find(r => r.id === currentRoom) || level.rooms[0];

  React.useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages]);

  const pickRoom = (id) => {
    const r = level.rooms.find(rr => rr.id === id);
    if (!r) return;
    setCurrentRoom(id);
    setVisited(v => new Set([...v, id]));
    setMessages(m => [
      ...m,
      { role: 'gm', text: `The party moves to ${r.name}.` },
      { role: 'dm', text: describeRoom(r) },
    ]);
  };

  const jumpLevel = (idx) => {
    setLevelIdx(idx);
    const first = dungeon.levels[idx].rooms[0];
    setCurrentRoom(first.id);
    setVisited(v => new Set([...v, first.id]));
    setMessages(m => [
      ...m,
      { role: 'system', text: `Descending to Level ${dungeon.levels[idx].id} · ${dungeon.levels[idx].name}` },
      { role: 'dm', text: describeRoom(first) },
    ]);
  };

  const send = () => {
    if (!draft.trim()) return;
    const q = draft;
    setMessages(m => [...m, { role: 'gm', text: q }]);
    setDraft('');
    setTimeout(() => {
      setMessages(m => [...m, { role: 'dm', text: generateDmReply(q, room, level, dungeon) }]);
    }, 450);
  };

  return (
    <div style={{ flex: 1, display: 'flex', minWidth: 0 }}>
      {/* LEFT — Dungeon Chat */}
      <div style={{
        width: 440, borderRight: '1px solid var(--line)',
        display: 'flex', flexDirection: 'column',
        background: 'var(--bg-1)',
      }}>
        <div style={{
          padding: '12px 18px',
          borderBottom: '1px solid var(--line-dim)',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span className="kicker">Dungeon Chat</span>
          <div style={{ flex: 1 }} />
          <div className="chip chip-teal">Turn 14</div>
          <div className="chip">{room.id}</div>
        </div>

        {/* Current room banner */}
        <div style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--line-dim)',
          background: 'linear-gradient(180deg, oklch(0.2 0.05 305 / 0.35), transparent)',
        }}>
          <div className="kicker" style={{ color: 'var(--violet)', marginBottom: 4 }}>
            Current Room
          </div>
          <div style={{
            fontFamily: 'var(--f-serif)', fontSize: 19, color: 'var(--ink-1)',
            lineHeight: 1.2, marginBottom: 3,
          }}>{room.name}</div>
          <div style={{ fontSize: 12, color: 'var(--ink-3)', marginTop: 4 }}>
            {room.note}
          </div>
        </div>

        <div ref={scrollRef} style={{
          flex: 1, overflow: 'auto',
          padding: '16px 18px',
        }}>
          {messages.map((m, i) => <PlayBubble key={i} {...m} />)}
        </div>

        <div style={{
          padding: 14,
          borderTop: '1px solid var(--line-dim)',
          background: 'var(--bg-0)',
        }}>
          <div style={{
            display: 'flex', gap: 8, marginBottom: 8, flexWrap: 'wrap',
          }}>
            {['Describe room', 'Search', 'Roll initiative', 'Listen'].map(s => (
              <button key={s} className="chip" style={{ cursor: 'pointer' }}
                      onClick={() => setDraft(s.toLowerCase())}>{s}</button>
            ))}
          </div>
          <div style={{
            display: 'flex', gap: 8, alignItems: 'flex-end',
            background: 'var(--bg-1)',
            border: '1px solid var(--line)',
            borderRadius: 10, padding: 10,
          }}>
            <textarea
              value={draft} onChange={e => setDraft(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); } }}
              rows={2}
              placeholder="Ask the dungeon anything — ‘what’s on the altar?’ · ‘the rogue checks for traps’"
              style={{
                flex: 1, background: 'transparent', border: 'none',
                color: 'var(--ink-1)', fontFamily: 'var(--f-ui)', fontSize: 13,
                resize: 'none', outline: 'none',
              }}
            />
            <button className="btn btn-primary" onClick={send}>Ask</button>
          </div>
        </div>
      </div>

      {/* RIGHT — Map viewer */}
      <div style={{
        flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column',
        background: 'var(--bg-0)',
      }}>
        <div style={{
          padding: '12px 18px',
          borderBottom: '1px solid var(--line-dim)',
          display: 'flex', alignItems: 'center', gap: 14,
        }}>
          <span className="kicker">Dungeon Viewer</span>
          <div style={{ flex: 1 }} />
          {/* Quest chip */}
          <div className="chip chip-gold">◇ Sundered Crown</div>
          {/* Jump to room */}
          <div style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '4px 10px',
            background: 'var(--bg-1)',
            border: '1px solid var(--line)',
            borderRadius: 999,
            fontFamily: 'var(--f-mono)', fontSize: 11, color: 'var(--ink-3)',
          }}>
            <span>Jump</span>
            <select
              value={currentRoom}
              onChange={e => pickRoom(e.target.value)}
              style={{
                background: 'transparent', border: 'none',
                color: 'var(--ink-1)', fontFamily: 'var(--f-mono)', fontSize: 11,
                outline: 'none', cursor: 'pointer',
              }}>
              {level.rooms.map(r => (
                <option key={r.id} value={r.id}
                  style={{ background: 'var(--bg-1)' }}>
                  {r.id} · {r.name}
                </option>
              ))}
            </select>
          </div>
        </div>

        <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
          {/* Map canvas */}
          <div style={{
            flex: 1, minWidth: 0, padding: 18,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            position: 'relative',
          }}>
            <div style={{
              width: '100%', height: '100%',
              border: '1px solid var(--line)',
              borderRadius: 8,
              overflow: 'hidden',
              background: 'var(--bg-0)',
              position: 'relative',
            }}>
              {/* Level heading overlay */}
              <div style={{
                position: 'absolute', top: 14, left: 16,
                zIndex: 2,
                pointerEvents: 'none',
              }}>
                <div className="kicker" style={{ color: 'var(--teal)' }}>
                  Level {level.id}
                </div>
                <div style={{
                  fontFamily: 'var(--f-serif)', fontSize: 22, color: 'var(--ink-1)',
                  letterSpacing: '0.01em',
                }}>{level.name}</div>
                <div style={{
                  fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-3)',
                  marginTop: 2,
                }}>{level.width} × {level.height} cells · 5 ft each</div>
              </div>

              {/* Legend */}
              <div style={{
                position: 'absolute', bottom: 14, left: 16,
                zIndex: 2,
                display: 'flex', gap: 10,
                padding: '7px 11px',
                background: 'oklch(0.12 0.02 285 / 0.75)',
                backdropFilter: 'blur(8px)',
                border: '1px solid var(--line-dim)',
                borderRadius: 6,
                fontFamily: 'var(--f-mono)', fontSize: 10,
                color: 'var(--ink-3)',
              }}>
                <span><span style={{ color: 'var(--teal)' }}>●</span> party</span>
                <span><span style={{ color: 'var(--violet)' }}>▢</span> shrine</span>
                <span><span style={{ color: 'var(--ember)' }}>▢</span> boss</span>
                <span><span style={{ color: 'var(--gold)' }}>▢</span> vault</span>
                <span><span style={{ color: 'var(--ink-4)' }}>▢</span> unseen</span>
              </div>

              {/* Variant selector */}
              <div style={{
                position: 'absolute', top: 14, right: 16, zIndex: 2,
                display: 'flex', gap: 3, padding: 3,
                background: 'oklch(0.12 0.02 285 / 0.8)',
                backdropFilter: 'blur(8px)',
                border: '1px solid var(--line)',
                borderRadius: 6,
              }}>
                {['grid', 'tiles', 'graph'].map(v => (
                  <button key={v}
                    onClick={() => onMapVariant(v)}
                    style={{
                      padding: '4px 10px', border: 'none',
                      background: mapVariant === v ? 'var(--bg-3)' : 'transparent',
                      color: mapVariant === v ? 'var(--ink-1)' : 'var(--ink-3)',
                      fontFamily: 'var(--f-mono)', fontSize: 10, letterSpacing: '0.1em',
                      textTransform: 'uppercase',
                      borderRadius: 4, cursor: 'pointer',
                    }}>{v}</button>
                ))}
              </div>

              <MapViewer level={level} variant={mapVariant}
                         currentRoom={currentRoom} onPickRoom={pickRoom}
                         visited={visited} activeLoop={activeLoop} />

              {/* Loop toggle strip */}
              {level.loops && level.loops.length > 0 && (
                <div style={{
                  position: 'absolute', bottom: 14, right: 16, zIndex: 2,
                  display: 'flex', gap: 6, padding: 5,
                  background: 'oklch(0.12 0.02 285 / 0.85)',
                  backdropFilter: 'blur(8px)',
                  border: '1px solid var(--line)', borderRadius: 6,
                }}>
                  <span style={{
                    fontFamily: 'var(--f-mono)', fontSize: 9, letterSpacing: '0.14em',
                    textTransform: 'uppercase', color: 'var(--ink-3)',
                    padding: '4px 6px 4px 8px', alignSelf: 'center',
                  }}>Loops</span>
                  {level.loops.map(lp => {
                    const pat = window.LOOP_PATTERNS[lp.pattern];
                    const isOn = activeLoop === lp.id;
                    return (
                      <button key={lp.id}
                        onClick={() => setActiveLoop(isOn ? null : lp.id)}
                        title={pat?.blurb}
                        style={{
                          padding: '4px 9px', border: '1px solid',
                          borderColor: isOn ? 'var(--teal)' : 'var(--line)',
                          background: isOn ? 'oklch(0.22 0.05 195 / 0.5)' : 'transparent',
                          color: isOn ? 'var(--ink-1)' : 'var(--ink-3)',
                          fontFamily: 'var(--f-mono)', fontSize: 10,
                          letterSpacing: '0.08em', textTransform: 'uppercase',
                          borderRadius: 4, cursor: 'pointer',
                        }}>{pat?.name || lp.pattern}</button>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Level stepper rail */}
          <div style={{
            width: 70, padding: '18px 12px',
            borderLeft: '1px solid var(--line)',
            background: 'var(--bg-1)',
            display: 'flex', flexDirection: 'column',
            alignItems: 'center', gap: 10,
          }}>
            <LevelStepper dungeon={dungeon} levelIdx={levelIdx} onLevelIdx={jumpLevel} />

            <div style={{
              width: 1, flex: 1,
              background: 'linear-gradient(180deg, transparent, var(--line-dim), transparent)',
              margin: '10px 0',
            }} />

            {dungeon.levels.map((lv, i) => (
              <button key={lv.id}
                onClick={() => jumpLevel(i)}
                style={{
                  width: 36, height: 36,
                  border: `1px solid ${i === levelIdx ? 'var(--teal)' : 'var(--line)'}`,
                  background: i === levelIdx ? 'oklch(0.22 0.05 195 / 0.4)' : 'var(--bg-2)',
                  color: i === levelIdx ? 'var(--ink-1)' : 'var(--ink-3)',
                  borderRadius: 6, cursor: 'pointer',
                  fontFamily: 'var(--f-serif)', fontSize: 14,
                  boxShadow: i === levelIdx ? '0 0 12px -2px var(--teal-glow)' : 'none',
                }}>{lv.id}</button>
            ))}

            <div style={{ flex: 1 }} />

            <div style={{
              width: 1, height: 30,
              background: 'linear-gradient(180deg, transparent, var(--line-dim), transparent)',
            }} />

            {/* compass */}
            <div style={{
              width: 36, height: 36, borderRadius: '50%',
              border: '1px solid var(--line)',
              display: 'grid', placeItems: 'center',
              color: 'var(--ink-4)', fontFamily: 'var(--f-serif)',
              fontSize: 11,
            }}>N</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function describeRoom(r) {
  return `${r.name}. ${r.note}`;
}

function generateDmReply(q, room, level, dungeon) {
  const lc = q.toLowerCase();
  if (lc.includes('describe') || lc.includes('look')) {
    return `${room.name}. ${room.note} You feel the weight of ${level.name.toLowerCase()} pressing around you — ${level.summary.toLowerCase()}`;
  }
  if (lc.includes('search')) {
    return `A careful sweep turns up ${room.type === 'vault' ? 'a silver offering bowl and two untouched gold angels' : room.type === 'boss' ? 'ritual markings, freshly redrawn' : 'dust, bone-shards, and one thing that shouldn’t be here — a wax seal bearing the crowned skull'}. Perception DC 14.`;
  }
  if (lc.includes('roll') || lc.includes('initiative')) {
    return `Initiative called. ${level.ecology} react to your presence. Roll d20+DEX; I’ll post the turn order once everyone’s in.`;
  }
  if (lc.includes('listen')) {
    return `You hold still. Beyond the basalt walls — water, always water — and beneath that a low arrhythmic scrape, as of stone dragged across stone. It is coming from the direction of ${level.rooms[level.rooms.length - 1].name}.`;
  }
  if (lc.includes('altar') || lc.includes('shrine')) {
    return `The altar of Mythrax is slick with brine. A channel has been carved recently — a fresh offering would wake something. The silver dust is iron filings, not silver.`;
  }
  if (lc.includes('trap')) {
    return `Investigation DC 13. You find a pressure seam along the threshold — triggers a pit, 10 ft, 1d6 bludgeoning. Easy to step around if you know.`;
  }
  return `The dungeon considers your question. ${room.note.split('.')[0]}. What does the party do?`;
}

Object.assign(window, { PlayMode });
