import { useCallback, useEffect, useRef, useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Activity, CircuitBoard, Cpu, FileText, FolderOpen, Library, MessageSquare, Package, RefreshCw, ShoppingBag, Sparkles } from 'lucide-react';
import { useConnection } from '../store/connection';
import { useZoom } from '../hooks/useZoom';
import { API_BASE } from '../lib/api';

const BACKOFF = [1, 2, 4, 8, 16, 30];

const navItems = [
  { to: '/', label: 'Dashboard', icon: Activity },
  { to: '/chat', label: 'Chat', icon: MessageSquare },
  { to: '/pcb', label: 'PCB', icon: CircuitBoard },
  { to: '/schematic', label: 'Schematic', icon: Cpu },
  { to: '/bom', label: 'BOM', icon: FileText },
  { to: '/library', label: 'Library', icon: Library },
  { to: '/marketplace', label: 'Market', icon: ShoppingBag },
  { to: '/files', label: 'Files', icon: FolderOpen },
  { to: '/fab', label: 'Fab', icon: Package },
  { to: '/demo', label: 'Demo', icon: Sparkles },
  { to: '/status', label: 'Status', icon: Activity },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  useZoom();
  const [collapsed, setCollapsed] = useState(false);
  const { state, lastError } = useConnection();
  const attemptRef = useRef(0);
  const timerRef = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const tick = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/api/v1/health`, { signal: AbortSignal.timeout(5000) });
      if (r.ok) { useConnection.setState({ state: "connected" }); attemptRef.current = 0; }
      else useConnection.setState({ state: "offline", lastError: `HTTP ${r.status}` });
    } catch (e) {
      useConnection.setState({ state: "offline", lastError: (e as Error).message });
    }
    attemptRef.current = Math.min(++attemptRef.current, BACKOFF.length - 1);
    timerRef.current = setTimeout(tick, BACKOFF[attemptRef.current] * 1000);
  }, []);

  useEffect(() => {
    tick();
    (async () => {
      try {
        const { listen } = await import("@tauri-apps/api/event");
        const unlisten = await listen("backend-status", (event: { payload: string }) => {
          if (event.payload === "ready") useConnection.setState({ state: "connected" });
          else if (event.payload?.startsWith("error:")) useConnection.setState({ state: "error", lastError: event.payload });
        });
        return () => { unlisten(); clearTimeout(timerRef.current); };
      } catch { return () => clearTimeout(timerRef.current); }
    })();
    return () => clearTimeout(timerRef.current);
  }, [tick]);

  const statusColor = state === "connected" ? "text-emerald-400" :
    state === "connecting" ? "text-amber-400" : "text-red-400";

  const statusLabel = state === "connected" ? "System Online" :
    state === "connecting" ? "Connecting..." : `Offline${lastError ? ` (${lastError.slice(0, 60)})` : ""}`;

  const handleRestart = async () => {
    try {
      const { invoke } = await import("@tauri-apps/api/core");
      await invoke("start_backend");
    } catch { /* not in Tauri */ }
  };

  return (
    <div className="flex h-screen">
      <aside className={`bg-gray-900 border-r border-gray-800 transition-all ${collapsed ? 'w-14' : 'w-56'}`}>
        <div className="p-3 border-b border-gray-800 flex items-center gap-2">
          <CircuitBoard size={20} className="text-emerald-400 shrink-0" />
          {!collapsed && <span className="font-semibold text-sm">KiCad MCP</span>}
        </div>
        <button
          className="w-full p-2 text-xs text-gray-500 hover:text-gray-300 border-b border-gray-800"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? '>' : '<'}
        </button>
        <nav className="p-2 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-2 py-2 rounded text-sm transition ${
                  isActive ? 'bg-emerald-900/40 text-emerald-300' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                }`
              }
            >
              <Icon size={16} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-11 flex items-center justify-end px-6 border-b border-gray-800 bg-gray-950 shrink-0">
          <div className="flex items-center gap-2 text-xs">
            <span data-testid="connection-status" className={`w-2 h-2 rounded-full ${statusColor} bg-current`} />
            <span data-testid="connection-label" className={statusColor}>{statusLabel}</span>
            {state !== "connected" && (
              <button data-testid="restart-backend" onClick={handleRestart} title="Restart Backend" className="ml-1 text-slate-400 hover:text-white transition-colors">
                <RefreshCw className="w-3 h-3" />
              </button>
            )}
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">{children}</main>
      </div>
    </div>
  );
}
