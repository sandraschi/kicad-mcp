import { useState } from 'react';
import { apiPost, apiGet } from '../lib/api';

export default function PcbPage() {
  const [fileName, setFileName] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const runTool = async (tool: string, args: Record<string, unknown> = {}) => {
    setLoading(true);
    try {
      const res = await apiPost(`/api/v1/control/${tool}`, { file_name: fileName, ...args });
      setResult(res);
    } catch (e) {
      setResult({ error: String(e) });
    }
    setLoading(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">PCB Operations</h1>

      <div className="flex gap-2 mb-4">
        <input
          className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
          placeholder="PCB filename (e.g. board.kicad_pcb)"
          value={fileName}
          onChange={(e) => setFileName(e.target.value)}
        />
      </div>

      <div className="flex flex-wrap gap-2 mb-6">
        {[
          { label: 'Board Info', tool: 'pcb_info' },
          { label: 'List Components', tool: 'pcb_list_components' },
          { label: 'DRC Check', tool: 'pcb_drc' },
          { label: 'Export STEP', tool: 'pcb_export_step' },
          { label: 'Export Gerber', tool: 'pcb_export_gerber' },
        ].map(({ label, tool }) => (
          <button
            key={tool}
            className="px-3 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded text-sm disabled:opacity-50"
            disabled={!fileName || loading}
            onClick={() => runTool(tool)}
          >
            {label}
          </button>
        ))}
      </div>

      {loading && <div className="text-gray-400 text-sm">Running...</div>}

      {result && (
        <pre className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-xs overflow-auto max-h-96">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
