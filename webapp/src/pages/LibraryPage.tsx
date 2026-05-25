import { useState } from 'react';
import { apiPost } from '../lib/api';

export default function LibraryPage() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'footprint' | 'symbol'>('footprint');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);

  const search = async () => {
    setLoading(true);
    const tool = mode === 'footprint' ? 'lib_find_footprint' : 'lib_find_symbol';
    try {
      const res = await apiPost(`/api/v1/control/${tool}`, { query, limit: 20 });
      setResult(res);
    } catch (e) {
      setResult({ error: String(e) });
    }
    setLoading(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Library Browser</h1>

      <div className="flex gap-2 mb-4">
        <button
          className={`px-3 py-2 rounded text-sm ${mode === 'footprint' ? 'bg-emerald-700' : 'bg-gray-800'}`}
          onClick={() => setMode('footprint')}
        >
          Footprints
        </button>
        <button
          className={`px-3 py-2 rounded text-sm ${mode === 'symbol' ? 'bg-emerald-700' : 'bg-gray-800'}`}
          onClick={() => setMode('symbol')}
        >
          Symbols
        </button>
      </div>

      <div className="flex gap-2 mb-6 max-w-md">
        <input
          className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
          placeholder={mode === 'footprint' ? 'Search footprints (e.g. SOIC-8)' : 'Search symbols (e.g. STM32F103)'}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
        />
        <button
          className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 rounded text-sm disabled:opacity-50"
          disabled={!query || loading}
          onClick={search}
        >
          Search
        </button>
      </div>

      {loading && <div className="text-gray-400 text-sm">Searching...</div>}

      {result && (
        <pre className="bg-gray-900 border border-gray-800 rounded-lg p-4 text-xs overflow-auto max-h-96">
          {JSON.stringify(result, null, 2)}
        </pre>
      )}
    </div>
  );
}
