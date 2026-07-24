import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiGet, apiPost } from '../lib/api';
import { Eye, Plus, RefreshCw, Search } from 'lucide-react';

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<any[]>([]);
  const [boardName, setBoardName] = useState('');
  const navigate = useNavigate();

  const refresh = useCallback(async () => {
    try { const d = await apiGet('/api/v1/review/list'); setReviews(d.reviews || []); } catch {}
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const createReview = async () => {
    try {
      const d = await apiPost(`/api/v1/review/create?board_name=${encodeURIComponent(boardName || 'unnamed')}`);
      if (d.review_id) navigate(`/review/${d.review_id}`);
    } catch {}
  };

  return (
    <div data-testid="reviews-page">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Design Reviews</h1>
        <button onClick={refresh} className="text-gray-400 hover:text-white p-1"><RefreshCw className="w-4 h-4" /></button>
      </div>

      <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-6">
        <h2 className="text-sm font-semibold mb-3">New Review</h2>
        <div className="flex gap-2">
          <input className="flex-1 bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-3 py-2 text-sm" placeholder="Board name (optional)" value={boardName} onChange={(e) => setBoardName(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && createReview()} />
          <button onClick={createReview} className="bg-emerald-600 hover:bg-emerald-500 text-white rounded px-4 py-2 text-sm flex items-center gap-1"><Plus className="w-4 h-4" /> Create</button>
        </div>
      </div>

      {reviews.length === 0 ? (
        <div className="text-gray-500 text-sm py-8 text-center">No design reviews yet. Create one above.</div>
      ) : (
        <div className="space-y-2">
          {reviews.map((r) => (
            <div key={r.id} className="bg-gray-900 border border-gray-800 rounded-lg p-4 flex items-center justify-between hover:border-gray-600 transition-colors cursor-pointer" onClick={() => navigate(`/review/${r.id}`)}>
              <div>
                <div className="text-sm font-medium">{r.board_name || 'Unnamed'}</div>
                <div className="text-xs text-gray-500 mt-1">Created {r.created_at?.slice(0, 10)} — {r.status}</div>
              </div>
              <div className="flex items-center gap-2">
                <span className={`text-xs px-2 py-0.5 rounded ${r.status === 'open' ? 'bg-amber-900/50 text-amber-300' : r.status === 'audited' ? 'bg-emerald-900/50 text-emerald-300' : 'bg-gray-800 text-gray-400'}`}>{r.status}</span>
                <Eye className="w-4 h-4 text-gray-500" />
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
