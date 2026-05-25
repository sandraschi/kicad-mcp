import { useState } from 'react';
import { apiPost } from '../lib/api';

export default function SchematicPage() {
  const [fileName, setFileName] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const runTool = async (tool: string) => {
    setLoading(true);
    try {
      const res = await apiPost(`/api/v1/control/${tool}`, { file_name: fileName });
      setResult(res);
    } catch (e) {
      setResult({ error: String(e) });
    }
    setLoading(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Schematic Operations</h1>

      <input
        className="w-full max-w-md bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm mb-4 block"
        placeholder="Schematic filename (e.g. project.kicad_sch)"
        value={fileName}
        onChange={(e) => setFileName(e.target.value)}
      />

      <div className="flex flex-wrap gap-2 mb-6">
        {[
          { label: 'Schematic Info', tool: 'sch_info' },
          { label: 'ERC Check', tool: 'sch_erc' },
          { label: 'Export Netlist', tool: 'sch_export_netlist' },
          { label: 'Export BOM', tool: 'sch_export_python_bom' },
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
