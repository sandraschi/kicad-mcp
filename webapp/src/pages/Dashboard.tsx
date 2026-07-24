import { useCallback, useEffect, useRef, useState } from 'react';
import { apiGet } from '../lib/api';
import { CircuitBoard, Cpu, Layers, RefreshCw, Wrench } from 'lucide-react';
import PcbViewer3D from '../components/PcbViewer3D';

export default function Dashboard() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [tools, setTools] = useState<string[]>([]);
  const [boardName, setBoardName] = useState('');
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  const fetchStatus = useCallback(() => {
    apiGet('/api/v1/status').then(setStatus).catch(console.error);
    apiGet('/api/v1/tools').then((d) => setTools(d.tools || [])).catch(console.error);
  }, []);

  useEffect(() => {
    fetchStatus();
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//127.0.0.1:11016/ws/board`;
    try {
      const ws = new WebSocket(wsUrl);
      ws.onopen = () => { setWsConnected(true); ws.send(JSON.stringify({ type: 'subscribe', channel: 'board' })); };
      ws.onclose = () => setWsConnected(false);
      ws.onerror = () => setWsConnected(false);
      wsRef.current = ws;
    } catch {}
    return () => { wsRef.current?.close(); };
  }, [fetchStatus]);

  const cards = [
    { label: 'Export CLI', value: status?.kicad_available ? '10.x ready' : 'Not Found', icon: Wrench, color: 'emerald' },
    { label: 'CRUD Backend', value: String(status?.crud_backend || status?.bridge_mode || 'none'), icon: Layers, color: 'blue' },
    { label: 'IPC Nightly', value: status?.ipc_api_server ? 'api-server' : 'not installed', icon: Cpu, color: 'purple' },
    { label: 'Tools Loaded', value: String(tools.length), icon: CircuitBoard, color: 'amber' },
  ];

  return (
    <div data-testid="dashboard">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">KiCad MCP Dashboard</h1>
        <div className="flex items-center gap-2 text-xs">
          <span className={`w-1.5 h-1.5 rounded-full ${wsConnected ? 'bg-emerald-400 animate-pulse' : 'bg-gray-600'}`} />
          <span className={wsConnected ? 'text-emerald-400' : 'text-gray-500'}>Live {wsConnected ? 'Connected' : 'Offline'}</span>
        </div>
      </div>

      {/* 3D Board Preview */}
      <div className="mb-6 bg-gray-900 border border-gray-800 rounded-lg overflow-hidden">
        <div className="px-4 py-2 border-b border-gray-800 flex items-center justify-between">
          <span className="text-xs text-gray-500">3D Board Preview</span>
          <button onClick={fetchStatus} className="text-gray-500 hover:text-white p-0.5" title="Refresh"><RefreshCw className="w-3 h-3" /></button>
        </div>
        <PcbViewer3D boardName={boardName} onBoardChange={setBoardName} />
      </div>

      <div className="grid grid-cols-4 gap-4 mb-8">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className={`bg-gray-900 border border-gray-800 rounded-lg p-4`} data-testid={`kpi-${label.toLowerCase().replace(/\s+/g, '-')}`}>
            <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
              <Icon size={14} className={`text-${color}-400`} />
              {label}
            </div>
            <div className="text-xl font-mono">{value}</div>
          </div>
        ))}
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Registered Tools ({tools.length})</h2>
        <div className="grid grid-cols-2 gap-1">
          {tools.map((t) => (
            <code key={t} className="text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded">{t}</code>
          ))}
        </div>
      </div>

      {status?.kicad_version ? (
        <div className="mt-4 text-xs text-gray-500 space-y-1">
          <div>Stable CLI: {String(status.kicad_version)}</div>
          {status.kicad_ipc_version ? <div>IPC CLI: {String(status.kicad_ipc_version)}</div> : null}
          {status.ipc_python_installed === false ? (
            <div className="text-amber-500">kicad-python not installed — run uv sync --extra ipc</div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}
