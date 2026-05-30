import { useEffect, useState } from 'react';
import { apiGet } from '../lib/api';
import { CircuitBoard, Cpu, Layers, Wrench } from 'lucide-react';

export default function Dashboard() {
  const [status, setStatus] = useState<Record<string, unknown> | null>(null);
  const [tools, setTools] = useState<string[]>([]);

  useEffect(() => {
    apiGet('/api/v1/status').then(setStatus).catch(console.error);
    apiGet('/api/v1/tools').then((d) => setTools(d.tools || [])).catch(console.error);
  }, []);

  const cards = [
    { label: 'Export CLI', value: status?.kicad_available ? '10.x ready' : 'Not Found', icon: Wrench, color: 'emerald' },
    { label: 'CRUD Backend', value: String(status?.crud_backend || status?.bridge_mode || 'none'), icon: Layers, color: 'blue' },
    { label: 'IPC Nightly', value: status?.ipc_api_server ? 'api-server' : 'not installed', icon: Cpu, color: 'purple' },
    { label: 'Tools Loaded', value: String(tools.length), icon: CircuitBoard, color: 'amber' },
  ];

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">KiCad MCP Dashboard</h1>
      <div className="grid grid-cols-4 gap-4 mb-8">
        {cards.map(({ label, value, icon: Icon, color }) => (
          <div key={label} className={`bg-gray-900 border border-gray-800 rounded-lg p-4`}>
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
