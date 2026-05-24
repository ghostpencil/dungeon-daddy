/* global React */
// Cyber-arcane desktop window chrome for Dungeon Daddy

function TrafficLights() {
  const dot = (bg) => (
    <div style={{
      width: 12, height: 12, borderRadius: '50%',
      background: bg,
      boxShadow: 'inset 0 0 0 0.5px rgba(0,0,0,0.4)',
    }} />
  );
  return (
    <div style={{ display: 'flex', gap: 8, alignItems: 'center', paddingLeft: 2 }}>
      {dot('#ff5f57')}{dot('#febc2e')}{dot('#28c840')}
    </div>
  );
}

function MenuBar({ appTitle = "Dungeon Daddy" }) {
  const items = ["File", "Edit", "Dungeon", "Play", "View", "Window", "Help"];
  const [now, setNow] = React.useState(() => new Date());
  React.useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 30000);
    return () => clearInterval(id);
  }, []);
  const time = now.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });
  return (
    <div style={{
      height: 26,
      display: 'flex', alignItems: 'center',
      background: 'linear-gradient(180deg, oklch(0.16 0.02 285 / 0.92), oklch(0.13 0.02 285 / 0.92))',
      backdropFilter: 'blur(20px)',
      borderBottom: '1px solid var(--line-dim)',
      padding: '0 12px',
      fontSize: 13, color: 'var(--ink-1)',
      fontFamily: 'var(--f-ui)',
    }}>
      {/* Arcane sigil mark */}
      <div style={{
        width: 14, height: 14, marginRight: 14,
        display: 'grid', placeItems: 'center',
      }}>
        <svg width="14" height="14" viewBox="0 0 14 14">
          <circle cx="7" cy="7" r="5.5" fill="none" stroke="var(--teal)" strokeWidth="1" />
          <path d="M7 2 L7 12 M2 7 L12 7 M3.5 3.5 L10.5 10.5 M10.5 3.5 L3.5 10.5"
                stroke="var(--violet)" strokeWidth="0.5" opacity="0.9" />
          <circle cx="7" cy="7" r="1.5" fill="var(--teal)" />
        </svg>
      </div>
      <div style={{ fontWeight: 700, marginRight: 18, letterSpacing: '0.01em' }}>{appTitle}</div>
      {items.map(i => (
        <div key={i} style={{
          padding: '2px 9px', borderRadius: 4, cursor: 'default',
          color: 'var(--ink-2)', fontSize: 13,
        }}
          onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-3)'}
          onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
        >{i}</div>
      ))}
      <div style={{ flex: 1 }} />
      <div style={{
        display: 'flex', alignItems: 'center', gap: 14,
        color: 'var(--ink-3)', fontFamily: 'var(--f-mono)', fontSize: 11,
      }}>
        <span>◐ moon waxing · d3 until new</span>
        <span style={{ color: 'var(--ink-2)' }}>{time}</span>
      </div>
    </div>
  );
}

function TitleBar({ title, mode, onMode }) {
  return (
    <div style={{
      height: 44,
      display: 'flex', alignItems: 'center',
      padding: '0 14px',
      background: 'linear-gradient(180deg, var(--bg-2), var(--bg-1))',
      borderBottom: '1px solid var(--line)',
      gap: 14,
    }}>
      <TrafficLights />
      <div style={{ width: 1, height: 16, background: 'var(--line-dim)', marginLeft: 4 }} />
      <div style={{
        fontFamily: 'var(--f-serif)', fontSize: 15, color: 'var(--ink-1)',
        letterSpacing: '0.02em',
      }}>{title}</div>

      <div style={{ flex: 1 }} />

      {/* Mode switch */}
      <div style={{
        display: 'flex', padding: 3,
        background: 'var(--bg-0)',
        border: '1px solid var(--line)',
        borderRadius: 999,
      }}>
        {["design", "play"].map(m => (
          <button key={m} onClick={() => onMode(m)} style={{
            appearance: 'none', border: 'none', cursor: 'pointer',
            padding: '5px 14px', borderRadius: 999,
            fontFamily: 'var(--f-mono)', fontSize: 10, letterSpacing: '0.18em',
            textTransform: 'uppercase',
            background: mode === m
              ? (m === 'design' ? 'linear-gradient(180deg, oklch(0.3 0.08 305), oklch(0.22 0.05 305))'
                                : 'linear-gradient(180deg, oklch(0.3 0.05 195), oklch(0.22 0.04 195))')
              : 'transparent',
            color: mode === m ? 'var(--ink-1)' : 'var(--ink-3)',
            boxShadow: mode === m
              ? (m === 'design' ? '0 0 18px -4px var(--violet-glow)' : '0 0 18px -4px var(--teal-glow)')
              : 'none',
            transition: 'all 160ms ease',
          }}>
            {m === 'design' ? '◆ Design' : '◈ Play'}
          </button>
        ))}
      </div>

      {/* Status pill */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '5px 12px',
        background: 'var(--bg-0)',
        border: '1px solid var(--line)',
        borderRadius: 999,
        fontFamily: 'var(--f-mono)', fontSize: 11,
        color: 'var(--ink-2)',
      }}>
        <span style={{
          width: 7, height: 7, borderRadius: '50%',
          background: 'var(--teal)',
          boxShadow: '0 0 8px var(--teal)',
        }} />
        Hearthfire · local
      </div>
    </div>
  );
}

function Window({ children, title, mode, onMode }) {
  return (
    <div style={{
      position: 'absolute', inset: 20,
      borderRadius: 14, overflow: 'hidden',
      background: 'var(--bg-1)',
      border: '1px solid var(--line)',
      boxShadow:
        '0 40px 80px -20px rgba(0,0,0,0.7), ' +
        '0 0 0 1px oklch(0.3 0.05 285 / 0.5), ' +
        '0 0 80px -20px var(--violet-glow)',
      display: 'flex', flexDirection: 'column',
      minWidth: 1200, minHeight: 760,
    }}>
      <MenuBar />
      <TitleBar title={title} mode={mode} onMode={onMode} />
      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {children}
      </div>
    </div>
  );
}

Object.assign(window, { Window, TrafficLights, MenuBar, TitleBar });
