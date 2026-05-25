import { useState } from 'react';
import { apiPost } from '../lib/api';

export default function BomPage() {
  const [fileName, setFileName] = useState('');
  const [format, setFormat] = useState('grouped_json');
  const [groupBy, setGroupBy] = useState('value');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const generate = async () => {
    setLoading(true);
    try {
      const res = await apiPost('/api/v1/control/bom_generate', {
        file_name: fileName,
        output_format: format,
        group_by: groupBy,
      });
      setResult(res);
    } catch (e) {
      setResult({ error: String(e) });
    }
    setLoading(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">BOM Generator</h1>

      <div className="space-y-3 mb-4 max-w-md">
        <input
          className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
          placeholder="PCB/Schematic filename"
          value={fileName}
          onChange={(e) => setFileName(e.target.value)}
        />
        <select className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" value={format} onChange={(e) => setFormat(e.target.value)}>
          <option value="grouped_json">Grouped JSON</option>
          <option value="json">Flat JSON</option>
          <option value="csv">CSV</option>
        </select>
        <select className="w-full bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm" value={groupBy} onChange={(e) => setGroupBy(e.target.value)}>
          <option value="value">Group by Value</option>
          <option value="footprint">Group by Footprint</option>
          <option value="none">No grouping</option>
        </select>
        <button
          className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 rounded text-sm disabled:opacity-50"
          disabled={!fileName || loading}
          onClick={generate}
        >
          Generate BOM
        </button>
      </div>

      {loading && <div className="text-gray-400 text-sm">Generating...</div>}

      {result && (
        <pre className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-xs overflow-auto max-h-96">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
