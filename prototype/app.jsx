/* global React, ReactDOM, Window, DesignMode, PlayMode */

const MAP_VARIANTS = ['grid', 'tiles', 'graph'];

const TWEAK_DEFAULS = /*EDITMODE-BEGIN*/{
  "mapVariant": "grid"
}/*EDITMODE-END*/;

function TweaksPanel({ open, onClose, mapVariant, setMapVariant }) {
  if (!open) return null;
  return (
    <div style={{
      position: 'fixed', bottom: 40, right: 40, zIndex: 99,
      width: 260,
      background: 'var(--bg-1)',
      border: '1px solid var(--line-hi)',
      borderRadius: 10,
      boxShadow: '0 20px 60px rgba(0,0,0,0.6), 0 0 40px -10px var(--violet-glow)',
      fontFamily: 'var(--f-ui)',
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '10px 14px',
        borderBottom: '1px solid var(--line-dim)',
      }}>
        <span style={{
          fontFamily: 'var(--f-serif)', fontSize: 14, color: 'var(--ink-1)',
        }}>Tweaks</span>
        <button onClick={onClose} style={{
          background: 'transparent', border: 'none', color: 'var(--ink-3)',
          cursor: 'pointer', fontSize: 16, lineHeight: 1,
        }}>×</button>
      </div>
      <div style={{ padding: 14 }}>
        <div className="kicker" style={{ marginBottom: 8 }}>Map Rendering</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {MAP_VARIANTS.map(v => (
            <button key={v} onClick={() => setMapVariant(v)}
              style={{
                textAlign: 'left', padding: '10px 12px',
                background: mapVariant === v ? 'oklch(0.22 0.05 195 / 0.4)' : 'var(--bg-0)',
                border: `1px solid ${mapVariant === v ? 'var(--teal-dim)' : 'var(--line)'}`,
                borderRadius: 6, cursor: 'pointer',
                color: 'var(--ink-1)', fontSize: 12,
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              }}>
              <span style={{ textTransform: 'capitalize' }}>{v}</span>
              <span style={{
                fontFamily: 'var(--f-mono)', fontSize: 10, color: 'var(--ink-3)',
              }}>
                {v === 'grid' ? 'graph paper' : v === 'tiles' ? 'tile sprites' : 'node graph'}
              </span>
            </button>
          ))}
        </div>
        <div style={{
          marginTop: 12, padding: 10,
          background: 'var(--bg-0)', border: '1px solid var(--line-dim)',
          borderRadius: 6,
          fontSize: 11, color: 'var(--ink-3)', lineHeight: 1.5,
        }}>
          All three render with shapes that port 1:1 to the Arcade 2D library (sprites, rects, lines).
        </div>
      </div>
    </div>
  );
}

function App() {
  const [mode, setMode] = React.useState(() => {
    return localStorage.getItem('dd-mode') || 'play';
  });
  const [mapVariant, setMapVariant] = React.useState(() => {
    return localStorage.getItem('dd-mapVariant') || TWEAK_DEFAULS.mapVariant || 'grid';
  });
  const [tweaksOpen, setTweaksOpen] = React.useState(false);

  React.useEffect(() => { localStorage.setItem('dd-mode', mode); }, [mode]);
  React.useEffect(() => { localStorage.setItem('dd-mapVariant', mapVariant); }, [mapVariant]);

  // Edit-mode protocol
  React.useEffect(() => {
    function handle(e) {
      if (!e.data || typeof e.data !== 'object') return;
      if (e.data.type === '__activate_edit_mode') setTweaksOpen(true);
      if (e.data.type === '__deactivate_edit_mode') setTweaksOpen(false);
    }
    window.addEventListener('message', handle);
    window.parent.postMessage({ type: '__edit_mode_available' }, '*');
    return () => window.removeEventListener('message', handle);
  }, []);

  const updateMapVariant = (v) => {
    setMapVariant(v);
    window.parent.postMessage({
      type: '__edit_mode_set_keys',
      edits: { mapVariant: v },
    }, '*');
  };

  const title = mode === 'design'
    ? 'Dungeon Daddy — Design · Tomb of the Forgotten King'
    : 'Dungeon Daddy — Play · Tomb of the Forgotten King';

  return (
    <>
      <Window title={title} mode={mode} onMode={setMode}>
        {mode === 'design'
          ? <DesignMode dungeon={window.DUNGEON} />
          : <PlayMode dungeon={window.DUNGEON}
              mapVariant={mapVariant} onMapVariant={updateMapVariant} />}
      </Window>
      <TweaksPanel
        open={tweaksOpen}
        onClose={() => setTweaksOpen(false)}
        mapVariant={mapVariant}
        setMapVariant={updateMapVariant}
      />
    </>
  );
}

ReactDOM.createRoot(document.getElementById('root')).render(<App />);
