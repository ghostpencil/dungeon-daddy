/* global React */
// Dungeon map viewer — renders a level as a 2D grid.
// Arcade 2D friendly: all geometry is solid rects / lines / simple polygons
// that map 1:1 to sprites or ShapeElementList in Arcade.
// Three styles via `variant`: "grid" | "tiles" | "graph"

function cellSize(level, canvasW, canvasH, padding = 24) {
  const w = (canvasW - padding * 2) / level.width;
  const h = (canvasH - padding * 2) / level.height;
  return Math.floor(Math.min(w, h));
}

// Find door-wall midpoints between two adjacent rooms (for connection rendering)
function connectionEndpoints(a, b) {
  // return midpoints of each room centered
  const ac = { x: a.x + a.w / 2, y: a.y + a.h / 2 };
  const bc = { x: b.x + b.w / 2, y: b.y + b.h / 2 };
  return [ac, bc];
}

function roomFill(type, dim = false) {
  const alpha = dim ? 0.45 : 1;
  switch (type) {
    case 'shrine': return `oklch(0.30 0.08 305 / ${alpha})`;
    case 'boss':   return `oklch(0.34 0.10 45 / ${alpha})`;
    case 'vault':  return `oklch(0.30 0.08 85 / ${alpha})`;
    case 'lair':   return `oklch(0.28 0.06 45 / ${alpha})`;
    case 'stair':  return `oklch(0.28 0.06 195 / ${alpha})`;
    case 'study':  return `oklch(0.28 0.05 305 / ${alpha})`;
    default:       return `oklch(0.26 0.03 285 / ${alpha})`;
  }
}

function roomStroke(type) {
  switch (type) {
    case 'shrine': return 'var(--violet)';
    case 'boss':   return 'var(--ember)';
    case 'vault':  return 'var(--gold)';
    case 'lair':   return 'oklch(0.65 0.14 45)';
    case 'stair':  return 'var(--teal)';
    case 'study':  return 'oklch(0.7 0.14 305)';
    default:       return 'oklch(0.55 0.04 285)';
  }
}

// ─────────────────────────────────────────────────────────────
// Grid variant — classic graph paper with walls and door glyphs
// ─────────────────────────────────────────────────────────────
function GridMap({ level, currentRoom, onPickRoom, visited }) {
  const W = 720, H = 520;
  const s = cellSize(level, W, H);
  const ox = (W - s * level.width) / 2;
  const oy = (H - s * level.height) / 2;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%"
         style={{ display: 'block', maxHeight: '100%' }}>
      <defs>
        <pattern id="gp" width={s} height={s} patternUnits="userSpaceOnUse">
          <rect width={s} height={s} fill="transparent" />
          <path d={`M ${s} 0 L 0 0 0 ${s}`} fill="none" stroke="oklch(0.32 0.02 285 / 0.5)" strokeWidth="0.5" />
        </pattern>
        <pattern id="gp-major" width={s * 5} height={s * 5} patternUnits="userSpaceOnUse">
          <path d={`M ${s*5} 0 L 0 0 0 ${s*5}`} fill="none" stroke="oklch(0.38 0.03 285 / 0.7)" strokeWidth="0.6" />
        </pattern>
        <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="2" />
        </filter>
      </defs>

      {/* background */}
      <rect x="0" y="0" width={W} height={H} fill="var(--bg-0)" />
      {/* grid within play area */}
      <rect x={ox} y={oy} width={s * level.width} height={s * level.height}
            fill="url(#gp)" />
      <rect x={ox} y={oy} width={s * level.width} height={s * level.height}
            fill="url(#gp-major)" />
      <rect x={ox} y={oy} width={s * level.width} height={s * level.height}
            fill="none" stroke="oklch(0.4 0.03 285)" strokeWidth="1" />

      {/* connections first (behind rooms) */}
      {level.connections.filter(c => !c.type.startsWith('stair_')).map((c, i) => {
        const a = level.rooms.find(r => r.id === c.from);
        const b = level.rooms.find(r => r.id === c.to);
        if (!a || !b) return null;
        const [p, q] = connectionEndpoints(a, b);
        return (
          <line key={i}
                x1={ox + p.x * s} y1={oy + p.y * s}
                x2={ox + q.x * s} y2={oy + q.y * s}
                stroke={c.type === 'hole' ? 'var(--ember)' : 'oklch(0.5 0.04 285)'}
                strokeWidth={c.type === 'arch' ? 6 : 3}
                strokeDasharray={c.type === 'hole' ? '4 4' : ''}
                opacity="0.7"
          />
        );
      })}

      {/* rooms */}
      {level.rooms.map(r => {
        const isCurrent = r.id === currentRoom;
        const seen = visited.has(r.id);
        return (
          <g key={r.id} style={{ cursor: 'pointer' }} onClick={() => onPickRoom(r.id)}>
            <rect
              x={ox + r.x * s} y={oy + r.y * s}
              width={r.w * s} height={r.h * s}
              fill={seen ? roomFill(r.type) : 'oklch(0.18 0.02 285)'}
              stroke={isCurrent ? 'var(--teal)' : (seen ? roomStroke(r.type) : 'oklch(0.3 0.02 285)')}
              strokeWidth={isCurrent ? 2 : 1}
              style={isCurrent ? { filter: 'drop-shadow(0 0 8px var(--teal))' } : {}}
            />
            {/* room number */}
            <text
              x={ox + (r.x + r.w / 2) * s}
              y={oy + (r.y + r.h / 2) * s + 4}
              textAnchor="middle"
              fill={seen ? 'var(--ink-1)' : 'var(--ink-4)'}
              fontFamily="var(--f-serif)"
              fontSize={Math.max(14, s * 0.8)}
              fontWeight="600"
            >{r.num}</text>
          </g>
        );
      })}

      {/* entries / stairs */}
      {level.entries.map((e, i) => (
        <g key={i}>
          <circle
            cx={ox + e.x * s} cy={oy + e.y * s} r={s * 0.5}
            fill="oklch(0.25 0.06 195)" stroke="var(--teal)" strokeWidth="1.5"
          />
          <text x={ox + e.x * s} y={oy + e.y * s + 3}
                textAnchor="middle" fill="var(--teal)"
                fontFamily="var(--f-mono)" fontSize="10">▼</text>
        </g>
      ))}

      {/* Room labels at top-right */}
      {level.rooms.map(r => {
        if (!visited.has(r.id)) return null;
        return (
          <text key={r.id + 'lbl'}
            x={ox + r.x * s + 4}
            y={oy + r.y * s + 11}
            fill="var(--ink-3)"
            fontFamily="var(--f-mono)" fontSize="9">
            {r.id}
          </text>
        );
      })}
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────
// Tiles variant — stylized top-down tiles w/ subtle shading
// Arcade-renderable as tiled sprite sheet
// ─────────────────────────────────────────────────────────────
function TilesMap({ level, currentRoom, onPickRoom, visited }) {
  const W = 720, H = 520;
  const s = cellSize(level, W, H);
  const ox = (W - s * level.width) / 2;
  const oy = (H - s * level.height) / 2;

  // Build cell occupancy
  const occupancy = {};
  level.rooms.forEach(r => {
    for (let x = r.x; x < r.x + r.w; x++) {
      for (let y = r.y; y < r.y + r.h; y++) {
        occupancy[`${x},${y}`] = r;
      }
    }
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" style={{ display: 'block' }}>
      <defs>
        <filter id="emboss">
          <feGaussianBlur stdDeviation="0.4" />
        </filter>
      </defs>
      <rect x="0" y="0" width={W} height={H} fill="#0a0a10" />

      {/* void texture */}
      <rect x={ox} y={oy} width={s * level.width} height={s * level.height}
            fill="oklch(0.10 0.02 285)" />

      {/* render each cell that belongs to a room */}
      {level.rooms.flatMap(r => {
        const seen = visited.has(r.id);
        const cells = [];
        for (let x = r.x; x < r.x + r.w; x++) {
          for (let y = r.y; y < r.y + r.h; y++) {
            const isEdgeTop = !occupancy[`${x},${y-1}`] || occupancy[`${x},${y-1}`].id !== r.id;
            const isEdgeLeft = !occupancy[`${x-1},${y}`] || occupancy[`${x-1},${y}`].id !== r.id;
            cells.push(
              <g key={`${r.id}-${x}-${y}`}>
                <rect
                  x={ox + x * s} y={oy + y * s}
                  width={s} height={s}
                  fill={seen
                    ? `oklch(${0.22 + ((x+y) % 2) * 0.02} 0.02 285)`
                    : 'oklch(0.13 0.015 285)'}
                  stroke="oklch(0.16 0.02 285)" strokeWidth="0.5"
                />
                {/* top bevel */}
                {isEdgeTop && (
                  <line x1={ox + x*s} y1={oy + y*s + 0.5}
                        x2={ox + (x+1)*s} y2={oy + y*s + 0.5}
                        stroke="oklch(0.3 0.03 285)" strokeWidth="1" />
                )}
                {isEdgeLeft && (
                  <line x1={ox + x*s + 0.5} y1={oy + y*s}
                        x2={ox + x*s + 0.5} y2={oy + (y+1)*s}
                        stroke="oklch(0.3 0.03 285)" strokeWidth="1" />
                )}
              </g>
            );
          }
        }
        return cells;
      })}

      {/* wall outlines for each room */}
      {level.rooms.map(r => {
        const seen = visited.has(r.id);
        const isCurrent = r.id === currentRoom;
        return (
          <g key={r.id} style={{ cursor: 'pointer' }} onClick={() => onPickRoom(r.id)}>
            <rect
              x={ox + r.x * s} y={oy + r.y * s}
              width={r.w * s} height={r.h * s}
              fill="none"
              stroke={isCurrent ? 'var(--teal)' : (seen ? roomStroke(r.type) : 'oklch(0.25 0.02 285)')}
              strokeWidth={isCurrent ? 2.5 : (seen ? 1.5 : 0.8)}
              style={isCurrent ? { filter: 'drop-shadow(0 0 6px var(--teal))' } : {}}
            />
            {isCurrent && (
              <circle
                cx={ox + (r.x + r.w/2) * s}
                cy={oy + (r.y + r.h/2) * s}
                r={s * 0.35}
                fill="var(--teal)"
                opacity="0.5"
              >
                <animate attributeName="opacity" values="0.3;0.7;0.3" dur="2s" repeatCount="indefinite" />
              </circle>
            )}
            <text
              x={ox + (r.x + r.w / 2) * s}
              y={oy + (r.y + r.h / 2) * s + 4}
              textAnchor="middle"
              fill={seen ? 'var(--ink-1)' : 'var(--ink-4)'}
              fontFamily="var(--f-serif)" fontSize={Math.max(12, s*0.7)} fontWeight="600"
              style={{ pointerEvents: 'none' }}
            >{r.num}</text>
          </g>
        );
      })}

      {/* connections on top as glowing lines */}
      {level.connections.filter(c => !c.type.startsWith('stair_')).map((c, i) => {
        const a = level.rooms.find(r => r.id === c.from);
        const b = level.rooms.find(r => r.id === c.to);
        if (!a || !b) return null;
        const [p, q] = connectionEndpoints(a, b);
        return (
          <line key={i}
                x1={ox + p.x * s} y1={oy + p.y * s}
                x2={ox + q.x * s} y2={oy + q.y * s}
                stroke="oklch(0.5 0.08 195 / 0.4)"
                strokeWidth="2"
                strokeDasharray={c.type === 'hole' ? '4 4' : ''}
          />
        );
      })}
    </svg>
  );
}

// ─────────────────────────────────────────────────────────────
// Graph variant — abstract node graph
// ─────────────────────────────────────────────────────────────
function GraphMap({ level, currentRoom, onPickRoom, visited }) {
  const W = 720, H = 520;
  const pad = 60;
  // Position nodes by their room centers
  const maxX = level.width, maxY = level.height;
  const nodePos = {};
  level.rooms.forEach(r => {
    nodePos[r.id] = {
      x: pad + ((r.x + r.w/2) / maxX) * (W - pad * 2),
      y: pad + ((r.y + r.h/2) / maxY) * (H - pad * 2),
    };
  });

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%" style={{ display: 'block' }}>
      <rect x="0" y="0" width={W} height={H} fill="var(--bg-0)" />
      {/* subtle dot grid */}
      <defs>
        <pattern id="dots" width="22" height="22" patternUnits="userSpaceOnUse">
          <circle cx="1" cy="1" r="0.8" fill="oklch(0.25 0.02 285)" />
        </pattern>
      </defs>
      <rect x="0" y="0" width={W} height={H} fill="url(#dots)" />

      {/* edges */}
      {level.connections.filter(c => !c.type.startsWith('stair_')).map((c, i) => {
        const p = nodePos[c.from], q = nodePos[c.to];
        if (!p || !q) return null;
        const mx = (p.x + q.x) / 2, my = (p.y + q.y) / 2;
        return (
          <g key={i}>
            <line x1={p.x} y1={p.y} x2={q.x} y2={q.y}
                  stroke={c.type === 'hole' ? 'var(--ember)' : 'oklch(0.45 0.04 285)'}
                  strokeWidth="1.5"
                  strokeDasharray={c.type === 'hole' ? '4 4' : ''}
            />
            <rect x={mx - 14} y={my - 7} width="28" height="14" rx="3"
                  fill="var(--bg-1)" stroke="oklch(0.3 0.03 285)" />
            <text x={mx} y={my + 3} textAnchor="middle"
                  fill="var(--ink-3)" fontFamily="var(--f-mono)" fontSize="8"
                  style={{ textTransform: 'uppercase', letterSpacing: '0.1em' }}>
              {c.type}
            </text>
          </g>
        );
      })}

      {/* nodes */}
      {level.rooms.map(r => {
        const p = nodePos[r.id];
        const isCurrent = r.id === currentRoom;
        const seen = visited.has(r.id);
        return (
          <g key={r.id} transform={`translate(${p.x},${p.y})`}
             style={{ cursor: 'pointer' }} onClick={() => onPickRoom(r.id)}>
            <circle r="26"
              fill={seen ? roomFill(r.type) : 'var(--bg-1)'}
              stroke={isCurrent ? 'var(--teal)' : (seen ? roomStroke(r.type) : 'oklch(0.3 0.02 285)')}
              strokeWidth={isCurrent ? 2 : 1.2}
              style={isCurrent ? { filter: 'drop-shadow(0 0 8px var(--teal))' } : {}}
            />
            <text y="6" textAnchor="middle"
                  fill={seen ? 'var(--ink-1)' : 'var(--ink-4)'}
                  fontFamily="var(--f-serif)" fontSize="18" fontWeight="600">{r.num}</text>
            <text y="44" textAnchor="middle"
                  fill="var(--ink-3)" fontFamily="var(--f-mono)" fontSize="9"
                  style={{ textTransform: 'uppercase', letterSpacing: '0.1em' }}>{r.type}</text>
          </g>
        );
      })}
    </svg>
  );
}

// Loop overlay — draws cycle arcs (path A teal, path B violet) through room centers
function LoopOverlay({ level, activeLoop }) {
  if (!activeLoop || !level.loops) return null;
  const loop = level.loops.find(l => l.id === activeLoop);
  if (!loop) return null;
  const W = 720, H = 520;
  const s = cellSize(level, W, H);
  const ox = (W - s * level.width) / 2;
  const oy = (H - s * level.height) / 2;

  const pts = (ids) => ids.map(id => {
    const r = level.rooms.find(rr => rr.id === id);
    return r ? { x: ox + (r.x + r.w/2) * s, y: oy + (r.y + r.h/2) * s } : null;
  }).filter(Boolean);

  const pathStr = (ps) => ps.map((p, i) => `${i===0?'M':'L'} ${p.x} ${p.y}`).join(' ');
  const A = pts(loop.path_a);
  const B = pts(loop.path_b);

  return (
    <svg viewBox={`0 0 ${W} ${H}`} width="100%" height="100%"
         style={{ position: 'absolute', inset: 0, pointerEvents: 'none' }}>
      <defs>
        <filter id="loopGlow"><feGaussianBlur stdDeviation="3" /></filter>
      </defs>
      <path d={pathStr(A)} fill="none" stroke="var(--teal)" strokeWidth="3"
            opacity="0.9" filter="url(#loopGlow)" />
      <path d={pathStr(A)} fill="none" stroke="var(--teal)" strokeWidth="1.5" />
      <path d={pathStr(B)} fill="none" stroke="var(--violet)" strokeWidth="3"
            opacity="0.9" filter="url(#loopGlow)" strokeDasharray="6 4" />
      <path d={pathStr(B)} fill="none" stroke="var(--violet)" strokeWidth="1.5"
            strokeDasharray="6 4" />
      {A[0] && (
        <g>
          <circle cx={A[0].x} cy={A[0].y} r="10" fill="var(--teal)" opacity="0.3" />
          <text x={A[0].x} y={A[0].y - 14} textAnchor="middle"
                fill="var(--teal)" fontFamily="var(--f-mono)" fontSize="9"
                style={{ textTransform: 'uppercase', letterSpacing: '0.12em' }}>entry</text>
        </g>
      )}
      {A[A.length-1] && (
        <g>
          <circle cx={A[A.length-1].x} cy={A[A.length-1].y} r="10" fill="var(--violet)" opacity="0.3" />
          <text x={A[A.length-1].x} y={A[A.length-1].y - 14} textAnchor="middle"
                fill="var(--violet)" fontFamily="var(--f-mono)" fontSize="9"
                style={{ textTransform: 'uppercase', letterSpacing: '0.12em' }}>goal</text>
        </g>
      )}
    </svg>
  );
}

function MapViewer({ level, variant, currentRoom, onPickRoom, visited, activeLoop }) {
  const Comp = variant === 'tiles' ? TilesMap
             : variant === 'graph' ? GraphMap
             : GridMap;
  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <Comp level={level} currentRoom={currentRoom} onPickRoom={onPickRoom} visited={visited} />
      <LoopOverlay level={level} activeLoop={activeLoop} />
    </div>
  );
}

Object.assign(window, { MapViewer, GridMap, TilesMap, GraphMap, LoopOverlay });
