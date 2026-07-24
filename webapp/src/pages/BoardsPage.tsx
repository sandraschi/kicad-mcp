import { useCallback, useEffect, useState } from 'react';
import { apiGet, apiPost } from '../lib/api';
import { Download, ExternalLink, Search, Star } from 'lucide-react';

export default function BoardsPage() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [downloading, setDownloading] = useState<string | null>(null);
  const [message, setMessage] = useState('');
  const [localBoards, setLocalBoards] = useState<string[]>([]);
  const [filterComplex, setFilterComplex] = useState(true);

  const search = useCallback(async () => {
    setLoading(true);
    setMessage('');
    try {
      const d = await apiGet(`/api/v1/boards?q=${encodeURIComponent(query)}&per_page=24&filter_complex=${filterComplex}`);
      if (d.success) { setResults(d.results); if (d.count === 0) setMessage('No boards found.'); }
      else setMessage(d.error || 'Search failed');
    } catch (e) { setMessage(String(e)); }
    setLoading(false);
  }, [query, filterComplex]);

  const download = useCallback(async (repo: string) => {
    setDownloading(repo);
    try {
      const d = await apiPost('/api/v1/control/boards_download', { repo });
      if (d.success) {
        setMessage(`Downloaded ${d.count} files from ${repo}`);
        const boards = await apiPost('/api/v1/board/preview', {});
        if (boards.boards) setLocalBoards(boards.boards.map((b: any) => b.name));
      } else setMessage(d.error || 'Download failed');
    } catch (e) { setMessage(String(e)); }
    setDownloading(null);
  }, []);

  useEffect(() => {
    apiPost('/api/v1/board/preview', {}).then((d) => {
      if (d.boards) setLocalBoards(d.boards.map((b: any) => b.name));
    }).catch(() => {});
  }, []);

  return (
    <div data-testid="boards-page">
      <h1 className="text-2xl font-bold mb-2">Board Marketplace</h1>
      <p className="text-sm text-gray-500 mb-4">Search GitHub for KiCad projects — small controller boards, Raspberry Pi hats, breakouts, and shields. Filtered to exclude complex boards.</p>

      <div className="flex gap-2 mb-4">
        <div className="flex-1 flex items-center gap-2 bg-zinc-800 border border-zinc-600 rounded-lg px-3 py-2">
          <Search className="w-4 h-4 text-gray-500 shrink-0" />
          <input className="flex-1 bg-transparent text-zinc-100 border-none outline-none text-sm" placeholder="Search boards (e.g. 'raspberry pi hat', 'stm32', 'audio dac')..." value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && search()} />
        </div>
        <button onClick={search} disabled={loading} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 text-white rounded-lg px-4 py-2 text-sm">Search</button>
        <button
          onClick={() => setFilterComplex(!filterComplex)}
          className={`px-3 py-2 rounded-lg text-xs border transition-colors ${filterComplex ? 'bg-zinc-800 text-zinc-300 border-zinc-600' : 'bg-amber-900/30 text-amber-300 border-amber-700'}`}
          title={filterComplex ? 'Filtering out complex boards. Click to show all.' : 'Showing all boards. Click to filter out complex ones.'}
        >
          {filterComplex ? 'Simple boards' : 'All boards'}
        </button>
      </div>

      {loading && <div className="text-gray-500 text-sm py-8 text-center">Searching GitHub for KiCad projects...</div>}
      {message && !loading && <div className="text-sm text-gray-400 mb-4">{message}</div>}

      <div className="grid grid-cols-2 lg:grid-cols-3 gap-3">
        {results.map((r) => (
          <div key={r.repo} className="bg-gray-900 border border-gray-800 rounded-lg p-4 hover:border-gray-600 transition-colors">
            <div className="flex items-start justify-between mb-2">
              <div className="min-w-0 flex-1">
                <a href={r.url} target="_blank" rel="noreferrer" className="text-sm font-medium text-emerald-400 hover:text-emerald-300 truncate block">
                  {r.repo} <ExternalLink className="w-3 h-3 inline" />
                </a>
              </div>
              <div className="flex items-center gap-1 text-xs text-amber-400 ml-2 shrink-0">
                <Star className="w-3 h-3" />{r.stars}
              </div>
            </div>
            {r.description && <p className="text-xs text-gray-500 mb-2 line-clamp-2">{r.description}</p>}
            <div className="flex items-center gap-1 flex-wrap mb-3">
              {r.topics?.slice(0, 4).map((t: string) => <span key={t} className="text-xs bg-zinc-800 text-zinc-400 px-1.5 py-0.5 rounded">{t}</span>)}
              <span className={`text-xs px-1.5 py-0.5 rounded ${r.score >= 8 ? 'bg-emerald-900/50 text-emerald-300' : 'bg-amber-900/50 text-amber-300'}`}>score {r.score}/10</span>
            </div>
            <button
              onClick={() => download(r.repo)}
              disabled={downloading === r.repo}
              className="w-full text-xs bg-gray-800 hover:bg-gray-700 disabled:bg-gray-800/50 text-gray-300 rounded px-3 py-1.5 flex items-center justify-center gap-1 transition-colors"
            >
              <Download className="w-3 h-3" /> {downloading === r.repo ? 'Downloading...' : 'Download KiCad Files'}
            </button>
          </div>
        ))}
      </div>

      {localBoards.length > 0 && (
        <div className="mt-8 bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-sm font-semibold mb-2">Downloaded Boards ({localBoards.length})</h2>
          <div className="flex flex-wrap gap-2">
            {localBoards.map((b) => <span key={b} className="text-xs bg-zinc-800 text-zinc-300 px-2 py-1 rounded">{b}</span>)}
          </div>
          <p className="text-xs text-gray-500 mt-2">Downloaded boards appear in the Dashboard 3D viewer's board selector.</p>
        </div>
      )}
    </div>
  );
}
