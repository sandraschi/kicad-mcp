import { useState } from 'react';
import { apiPost } from '../lib/api';

const SOURCES = [
  { id: 'all', label: 'All Sources' },
  { id: 'github', label: 'GitHub' },
  { id: 'kitspace', label: 'Kitspace' },
  { id: 'snapeda', label: 'SnapEDA' },
];

const TOPICS: Record<string, { id: string; label: string }[]> = {
  github: [
    { id: 'kicad', label: 'KiCad' },
    { id: 'esp32', label: 'ESP32' },
    { id: 'arduino', label: 'Arduino' },
    { id: 'stm32', label: 'STM32' },
    { id: 'audio', label: 'Audio' },
    { id: 'power-supply', label: 'Power' },
    { id: 'rf', label: 'RF' },
    { id: 'sensor', label: 'Sensors' },
  ],
  snapeda: [
    { id: 'connector', label: 'Connectors' },
    { id: 'microcontroller', label: 'MCUs' },
    { id: 'sensor', label: 'Sensors' },
    { id: 'power', label: 'Power ICs' },
    { id: 'passive', label: 'Passives' },
  ],
};

export default function MarketplacePage() {
  const [query, setQuery] = useState('');
  const [source, setSource] = useState('all');
  const [topic, setTopic] = useState('kicad');
  const [results, setResults] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(false);
  const [partQuery, setPartQuery] = useState('');
  const [partResults, setPartResults] = useState<Record<string, unknown> | null>(null);
  const [partLoading, setPartLoading] = useState(false);

  const search = async () => {
    setLoading(true);
    try {
      const res = await apiPost('/api/v1/control/marketplace_search', {
        source,
        query,
        topic: source === 'snapeda' ? '' : topic,
        limit: 20,
      });
      setResults(res?.data?.results || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  };

  const searchParts = async () => {
    setPartLoading(true);
    try {
      const res = await apiPost('/api/v1/control/parts_search', { query: partQuery, source: 'all', limit: 20 });
      setPartResults(res);
    } catch (e) {
      console.error(e);
    }
    setPartLoading(false);
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Schematics & Parts Marketplace</h1>

      {/* ── Schematics Search ──────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6">
        <h2 className="text-lg font-semibold mb-3">Find KiCad Projects</h2>

        <div className="flex flex-wrap gap-2 mb-3">
          {SOURCES.map(({ id, label }) => (
            <button
              key={id}
              className={`px-3 py-1.5 rounded text-xs ${source === id ? 'bg-emerald-700' : 'bg-gray-800'}`}
              onClick={() => setSource(id)}
            >
              {label}
            </button>
          ))}
        </div>

        {source !== 'snapeda' && source !== 'all' && TOPICS[source] && (
          <div className="flex flex-wrap gap-1.5 mb-3">
            {TOPICS[source].map(({ id, label }) => (
              <button
                key={id}
                className={`px-2 py-1 rounded text-xs ${topic === id ? 'bg-blue-800' : 'bg-gray-800'}`}
                onClick={() => setTopic(id)}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        <div className="flex gap-2">
          <input
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
            placeholder={source === 'snapeda' ? 'Part number (e.g. STM32F103C8T6)' : 'Search projects (e.g. ESP32 breakout)'}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && search()}
          />
          <button
            className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 rounded text-sm disabled:opacity-50"
            disabled={loading}
            onClick={search}
          >
            Search
          </button>
        </div>
      </div>

      {loading && <div className="text-gray-400 text-sm mb-4">Searching...</div>}

      {results.length > 0 && (
        <div className="space-y-2 mb-8">
          {results.map((r, i) => {
            const isGh = String(r.source || '') === 'github';
            return (
              <div key={i} className="bg-gray-900 border border-gray-800 rounded-lg p-3 flex justify-between items-start">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs px-1.5 py-0.5 rounded bg-gray-800 text-gray-400">{String(r.source).toUpperCase()}</span>
                    <span className="font-medium text-sm">{String(r.name || '')}</span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">{String(r.description || '').slice(0, 200)}</div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {isGh && <span className="text-xs text-yellow-400">{String(r.stars || 0)} stars</span>}
                  <a
                    href={String(r.url || '#')}
                    target="_blank"
                    rel="noreferrer"
                    className="px-2 py-1 bg-gray-700 hover:bg-gray-600 rounded text-xs text-gray-300"
                  >
                    Open
                  </a>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* ── Parts Search ──────────────────────────────────── */}
      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
        <h2 className="text-lg font-semibold mb-3">Find Component Parts</h2>
        <p className="text-xs text-gray-500 mb-3">
          Searches SnapEDA, KiCad built-in libraries, and community repos for footprints, symbols, and 3D models.
          Set <code className="bg-gray-800 px-1 rounded">SNAPEDA_API_KEY</code> for SnapEDA access.
        </p>

        <div className="flex gap-2 mb-3">
          <input
            className="flex-1 bg-gray-800 border border-gray-700 rounded px-3 py-2 text-sm"
            placeholder="Part number or description (e.g. LM358, 10uF 0805)"
            value={partQuery}
            onChange={(e) => setPartQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && searchParts()}
          />
          <button
            className="px-4 py-2 bg-emerald-700 hover:bg-emerald-600 rounded text-sm disabled:opacity-50"
            disabled={partLoading}
            onClick={searchParts}
          >
            Find Parts
          </button>
        </div>

        {partLoading && <div className="text-gray-400 text-sm">Searching...</div>}

        {partResults && (
          <pre className="bg-gray-800 rounded p-3 text-xs overflow-auto max-h-64">
            {JSON.stringify(partResults, null, 2)}
          </pre>
        )}
      </div>
    </div>
  );
}
