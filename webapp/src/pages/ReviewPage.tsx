import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { apiGet, apiPost } from '../lib/api';
import { Circle, Flag, RefreshCw, Send, Sparkles, X } from 'lucide-react';

export default function ReviewPage() {
  const { id } = useParams<{ id: string }>();
  const [review, setReview] = useState<any>(null);
  const [annotations, setAnnotations] = useState<any[]>([]);
  const [comment, setComment] = useState('');
  const [sev, setSev] = useState('info');
  const [xMm, setXMm] = useState('0');
  const [yMm, setYMm] = useState('0');
  const [layer, setLayer] = useState('F.Cu');
  const [auditResult, setAuditResult] = useState<any>(null);
  const [auditing, setAuditing] = useState(false);
  const svgRef = useRef<SVGSVGElement>(null);

  const refresh = useCallback(async () => {
    if (!id) return;
    try {
      const d = await apiGet(`/api/v1/review/${id}`);
      setReview(d.review);
      setAnnotations(d.annotations || []);
    } catch {}
  }, [id]);

  useEffect(() => { refresh(); }, [refresh]);

  const addAnnotation = async () => {
    if (!comment.trim()) return;
    try {
      await apiPost(`/api/v1/review/${id}/annotate`, { x_mm: Number(xMm), y_mm: Number(yMm), layer, comment, severity: sev });
      setComment('');
      refresh();
    } catch {}
  };

  const runAiAudit = async () => {
    setAuditing(true);
    try {
      const d = await apiPost(`/api/v1/review/${id}/ai-audit`);
      setAuditResult(d.suggestions || []);
      refresh();
    } catch {}
    setAuditing(false);
  };

  const sevColor: Record<string, string> = { critical: 'text-red-400', major: 'text-amber-400', minor: 'text-blue-400', info: 'text-gray-400' };

  return (
    <div data-testid="review-page" className="flex gap-4 h-full">
      {/* Board view */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-4">
          <h1 className="text-2xl font-bold">{review?.board_name || 'Design Review'}</h1>
          <button onClick={refresh} className="text-gray-400 hover:text-white p-1"><RefreshCw className="w-4 h-4" /></button>
        </div>

        {/* SVG board representation with annotations */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4 mb-4">
          <svg ref={svgRef} viewBox="0 0 400 300" className="w-full h-64 bg-zinc-950 rounded">
            {/* Board outline */}
            <rect x="50" y="40" width="300" height="220" fill="#0d5e2e" stroke="#1a7a3e" strokeWidth="2" rx="5" />
            {/* Copper traces */}
            {[...Array(12)].map((_, i) => (
              <line key={`t${i}`} x1={60 + Math.random() * 280} y1={50 + Math.random() * 200} x2={60 + Math.random() * 280} y2={50 + Math.random() * 200} stroke="#cd7f32" strokeWidth="1.5" opacity={0.6} />
            ))}
            {/* ICs */}
            {[...Array(4)].map((_, i) => (
              <rect key={`ic${i}`} x={80 + i * 80} y={80 + (i % 2) * 80} width={30} height={30} fill="#222" stroke="#444" strokeWidth="1" rx="2" />
            ))}
            {/* Annotation markers */}
            {annotations.map((a, i) => {
              const sx = 50 + (a.x_mm || i * 30) % 300;
              const sy = 40 + (a.y_mm || i * 40) % 220;
              return (
                <g key={a.id}>
                  <circle cx={sx} cy={sy} r="6" fill="none" stroke={a.severity === 'critical' ? '#f87171' : a.severity === 'major' ? '#fbbf24' : '#60a5fa'} strokeWidth="2" />
                  <text x={sx + 8} y={sy + 3} fill="#e2e8f0" fontSize="8">{a.severity}: {a.comment.slice(0, 20)}</text>
                </g>
              );
            })}
          </svg>
          <div className="text-xs text-gray-500 mt-2">Click on the board to set annotation coordinates (x, y mm). Board: 400x300 viewport.</div>
        </div>

        {/* Add annotation */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold mb-3">Add Annotation</h3>
          <div className="grid grid-cols-4 gap-2 mb-2 text-xs">
            <input className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5" placeholder="X (mm)" type="number" value={xMm} onChange={(e) => setXMm(e.target.value)} />
            <input className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5" placeholder="Y (mm)" type="number" value={yMm} onChange={(e) => setYMm(e.target.value)} />
            <select value={layer} onChange={(e) => setLayer(e.target.value)} className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5">
              <option>F.Cu</option><option>B.Cu</option><option>F.SilkS</option>
            </select>
            <select value={sev} onChange={(e) => setSev(e.target.value)} className="bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5">
              <option value="info">Info</option><option value="minor">Minor</option><option value="major">Major</option><option value="critical">Critical</option>
            </select>
          </div>
          <div className="flex gap-2">
            <input className="flex-1 bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-3 py-2 text-sm" placeholder="Annotation comment..." value={comment} onChange={(e) => setComment(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && addAnnotation()} />
            <button onClick={addAnnotation} disabled={!comment.trim()} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 text-white rounded px-3 py-2"><Send className="w-4 h-4" /></button>
          </div>
        </div>
      </div>

      {/* Sidebar */}
      <div className="w-72 shrink-0 space-y-4">
        {/* AI Audit */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold mb-3 flex items-center gap-1"><Sparkles className="w-3.5 h-3.5 text-amber-400" /> AI Audit</h3>
          <button onClick={runAiAudit} disabled={auditing} className="w-full bg-amber-700 hover:bg-amber-600 disabled:bg-gray-700 text-white rounded px-3 py-2 text-sm">{auditing ? 'Auditing...' : 'Run AI DRC Audit'}</button>
          {auditResult && (
            <div className="mt-3 text-xs space-y-1">
              {auditResult.map((s: string, i: number) => <p key={i} className="text-gray-300">• {s}</p>)}
            </div>
          )}
        </div>

        {/* Annotation list */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h3 className="text-sm font-semibold mb-3">Annotations ({annotations.length})</h3>
          {annotations.length === 0 ? (
            <p className="text-xs text-gray-500">No annotations yet.</p>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {annotations.map((a) => (
                <div key={a.id} className="text-xs bg-gray-800 rounded p-2">
                  <div className={`flex items-center gap-1 ${sevColor[a.severity] || 'text-gray-400'}`}>
                    <Circle className="w-2 h-2 fill-current" /> {a.severity}
                  </div>
                  <p className="text-gray-300 mt-1">{a.comment}</p>
                  <p className="text-gray-500 mt-0.5">{a.x_mm}, {a.y_mm}mm on {a.layer}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
