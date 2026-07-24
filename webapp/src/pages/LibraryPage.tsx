import { useCallback, useEffect, useRef, useState } from 'react';
import { apiGet, apiPost } from '../lib/api';
import { ExternalLink, Package, Search, X } from 'lucide-react';

export default function LibraryPage() {
  const [query, setQuery] = useState('');
  const [mode, setMode] = useState<'footprint' | 'symbol'>('footprint');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [selected, setSelected] = useState<any>(null);
  const [detail, setDetail] = useState<any>(null);
  const [filterPkg, setFilterPkg] = useState('');
  const [filterPinsMin, setFilterPinsMin] = useState('');
  const [filterPinsMax, setFilterPinsMax] = useState('');
  const detailRef = useRef<HTMLDivElement>(null);

  const search = useCallback(async () => {
    if (!query.trim()) return;
    setLoading(true);
    setSelected(null);
    setDetail(null);
    const tool = mode === 'footprint' ? 'lib_find_footprint' : 'lib_find_symbol';
    try {
      const res = await apiPost(`/api/v1/control/${tool}`, { query, limit: 50 });
      const items = res?.data?.footprints || res?.data?.symbols || [];
      setResults(items.slice(0, 50));
    } catch {
      // Fallback: use marketplace search with parametric
      try {
        const res = await apiPost('/api/v1/control/marketplace_search', { query, limit: 20 });
        setResults(res?.data?.results || []);
      } catch {
        setResults([]);
      }
    }
    setLoading(false);
  }, [query, mode]);

  const showDetail = useCallback(async (name: string) => {
    setSelected(name);
    try {
      const d = await apiGet(`/api/v1/component/${encodeURIComponent(name)}`);
      setDetail(d?.data || d);
    } catch {
      setDetail({ description: 'No details available' });
    }
    setTimeout(() => detailRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
  }, []);

  const filtered = results.filter((r: any) => {
    const name = (r.name || r.description || '').toLowerCase();
    if (filterPkg && !name.includes(filterPkg.toLowerCase())) return false;
    return true;
  });

  useEffect(() => { if (query) search(); }, [mode]);

  return (
    <div className="flex gap-4 h-full">
      {/* Main panel */}
      <div className="flex-1 min-w-0">
        <h1 className="text-2xl font-bold mb-4">Component Library</h1>

        {/* Mode + search */}
        <div className="flex gap-2 mb-3">
          {['footprint', 'symbol'].map((m) => (
            <button key={m} onClick={() => setMode(m as any)} className={`px-3 py-1.5 rounded text-xs ${mode === m ? 'bg-emerald-700 text-white' : 'bg-gray-800 text-gray-400'}`}>{m === 'footprint' ? 'Footprints' : 'Symbols'}</button>
          ))}
        </div>

        {/* Parametric filter bar */}
        <div className="flex gap-2 mb-3 flex-wrap">
          <div className="flex items-center gap-1">
            <Search className="w-3.5 h-3.5 text-gray-500" />
            <input className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 text-xs w-48" placeholder={mode === 'footprint' ? 'Search footprints...' : 'Search symbols...'} value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} />
          </div>
          <input className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 text-xs w-24" placeholder="Package" value={filterPkg} onChange={(e) => setFilterPkg(e.target.value)} />
          <input className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 text-xs w-20" placeholder="Pins min" type="number" value={filterPinsMin} onChange={(e) => setFilterPinsMin(e.target.value)} />
          <input className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 text-xs w-20" placeholder="Pins max" type="number" value={filterPinsMax} onChange={(e) => setFilterPinsMax(e.target.value)} />
          <button onClick={search} disabled={!query || loading} className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 disabled:bg-gray-700 text-white rounded text-xs">Search</button>
        </div>

        {/* Results */}
        {loading && <div className="text-gray-500 text-sm py-4">Searching...</div>}
        {!loading && filtered.length === 0 && query && <div className="text-gray-500 text-sm py-4">No components found for "{query}"</div>}
        {!loading && !query && <div className="text-gray-500 text-sm py-4">Enter a search term above to browse the component library.</div>}

        <div className="grid grid-cols-2 gap-2">
          {filtered.map((r: any, i: number) => {
            const name = r.name || r.description || r.footprint || `result-${i}`;
            return (
              <button key={name} onClick={() => showDetail(name)} className={`text-left bg-gray-900 border ${selected === name ? 'border-emerald-600' : 'border-gray-800'} rounded-lg p-3 hover:border-gray-600 transition-colors`}>
                <div className="flex items-center gap-2">
                  <Package className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                  <span className="text-sm font-mono truncate">{name}</span>
                </div>
                {(r.description || r.manufacturer) && <p className="text-xs text-gray-500 mt-1 truncate">{r.description || r.manufacturer}</p>}
              </button>
            );
          })}
        </div>
      </div>

      {/* Detail panel */}
      {selected && (
        <div ref={detailRef} className="w-80 shrink-0 bg-gray-900 border border-gray-800 rounded-lg p-4 overflow-y-auto max-h-[calc(100vh-12rem)]">
          <div className="flex items-center justify-between mb-3">
            <h2 className="font-semibold text-sm truncate">{selected}</h2>
            <button onClick={() => { setSelected(null); setDetail(null); }} className="text-gray-500 hover:text-white p-1"><X className="w-3.5 h-3.5" /></button>
          </div>
          {detail ? (
            <div className="space-y-2 text-xs">
              <div><span className="text-gray-500">Manufacturer:</span> <span className="text-gray-200">{detail.manufacturer || 'N/A'}</span></div>
              <div><span className="text-gray-500">Package:</span> <span className="text-gray-200">{detail.package || 'N/A'}</span></div>
              <div><span className="text-gray-500">Pins:</span> <span className="text-gray-200">{detail.pins || 'N/A'}</span></div>
              <div><span className="text-gray-500">Description:</span> <span className="text-gray-200">{detail.description || 'N/A'}</span></div>
              <div><span className="text-gray-500">Stock:</span> <span className="text-gray-200">{detail.stock?.toLocaleString() || 'N/A'}</span></div>
              {detail.price_1k && <div><span className="text-gray-500">Price (1k):</span> <span className="text-emerald-400">${detail.price_1k}</span></div>}
              {detail.datasheet && (
                <a href={detail.datasheet} target="_blank" rel="noreferrer" className="flex items-center gap-1 text-blue-400 hover:text-blue-300 mt-2">
                  <ExternalLink className="w-3 h-3" /> Datasheet
                </a>
              )}
            </div>
          ) : (
            <div className="text-gray-500 text-sm">Loading...</div>
          )}
        </div>
      )}
    </div>
  );
}
