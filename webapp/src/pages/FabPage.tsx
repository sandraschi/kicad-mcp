import { useCallback, useEffect, useState } from 'react';
import { apiGet, apiPost } from '../lib/api';
import { Download, ExternalLink, Package, RefreshCw } from 'lucide-react';

export default function FabPage() {
  const [orders, setOrders] = useState<any[]>([]);
  const [boardName, setBoardName] = useState('');
  const [fabHouse, setFabHouse] = useState('jlcpcb');
  const [quantity, setQuantity] = useState(5);
  const [layers, setLayers] = useState(2);
  const [color, setColor] = useState('green');
  const [widthMm, setWidthMm] = useState(100);
  const [heightMm, setHeightMm] = useState(100);
  const [exportResult, setExportResult] = useState<any>(null);

  const refresh = useCallback(async () => {
    try { const d = await apiGet('/api/v1/fab/orders'); setOrders(d.orders || []); } catch {}
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const handleExport = async () => {
    if (!boardName.trim()) return;
    try {
      const r = await apiPost(`/api/v1/fab/export?board_name=${encodeURIComponent(boardName)}`);
      setExportResult(r);
    } catch (e) { setExportResult({ success: false, error: String(e) }); }
  };

  const handleOrder = async () => {
    if (!boardName.trim()) return;
    try {
      await apiPost('/api/v1/fab/order', { board_name: boardName, fab_house: fabHouse, quantity, layer_count: layers, pcb_color: color, width_mm: widthMm, height_mm: heightMm });
      refresh();
    } catch {}
  };

  const estimatedPrice = ((widthMm * heightMm) / 10000 * quantity * 1.5).toFixed(2);

  return (
    <div data-testid="fab-page">
      <h1 className="text-2xl font-bold mb-6">Fabrication Pipeline</h1>

      <div className="grid grid-cols-2 gap-6">
        {/* Export card */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-3 flex items-center gap-2"><Package className="w-4 h-4 text-amber-400" />Generate Gerbers</h2>
          <input className="w-full bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-3 py-2 text-sm mb-3" placeholder="Board file name (e.g. design.kicad_pcb)" value={boardName} onChange={(e) => setBoardName(e.target.value)} />
          <button onClick={handleExport} disabled={!boardName.trim()} className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 text-white rounded px-4 py-2 text-sm transition-colors">
            Export & Zip Gerbers
          </button>
          {exportResult && (
            <div className={`mt-3 text-sm ${exportResult.success ? 'text-emerald-400' : 'text-red-400'}`}>
              {exportResult.success ? `Exported ${exportResult.file_count} files (${(exportResult.size_bytes / 1024).toFixed(1)} KB)` : exportResult.error}
            </div>
          )}
        </div>

        {/* Order form */}
        <div className="bg-gray-900 border border-gray-800 rounded-lg p-4">
          <h2 className="text-lg font-semibold mb-3">Place Order</h2>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <label className="text-gray-500 text-xs">Fab House</label>
              <select value={fabHouse} onChange={(e) => setFabHouse(e.target.value)} className="w-full bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 mt-1">
                <option value="jlcpcb">JLCPCB</option>
                <option value="pcbway">PCBWay</option>
              </select>
            </div>
            <div>
              <label className="text-gray-500 text-xs">Layers</label>
              <select value={layers} onChange={(e) => setLayers(Number(e.target.value))} className="w-full bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 mt-1">
                <option value={1}>1</option><option value={2}>2</option><option value={4}>4</option><option value={6}>6</option>
              </select>
            </div>
            <div>
              <label className="text-gray-500 text-xs">Qty</label>
              <input type="number" min={1} max={1000} value={quantity} onChange={(e) => setQuantity(Number(e.target.value))} className="w-full bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 mt-1" />
            </div>
            <div>
              <label className="text-gray-500 text-xs">PCB Color</label>
              <select value={color} onChange={(e) => setColor(e.target.value)} className="w-full bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 mt-1">
                <option value="green">Green</option><option value="blue">Blue</option><option value="red">Red</option><option value="black">Black</option><option value="white">White</option>
              </select>
            </div>
            <div><label className="text-gray-500 text-xs">Width (mm)</label><input type="number" min={10} max={500} value={widthMm} onChange={(e) => setWidthMm(Number(e.target.value))} className="w-full bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 mt-1" /></div>
            <div><label className="text-gray-500 text-xs">Height (mm)</label><input type="number" min={10} max={500} value={heightMm} onChange={(e) => setHeightMm(Number(e.target.value))} className="w-full bg-zinc-800 text-zinc-100 border border-zinc-600 rounded px-2 py-1.5 mt-1" /></div>
          </div>
          <div className="mt-3 text-sm text-gray-400">Est. price: <span className="text-emerald-400 font-mono">${estimatedPrice}</span></div>
          <button onClick={handleOrder} disabled={!boardName.trim()} className="mt-3 bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 text-white rounded px-4 py-2 text-sm transition-colors w-full">
            Submit Order
          </button>
        </div>
      </div>

      {/* Order history */}
      <div className="mt-6 bg-gray-900 border border-gray-800 rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold">Order History</h2>
          <button onClick={refresh} className="text-gray-400 hover:text-white p-1" title="Refresh"><RefreshCw className="w-4 h-4" /></button>
        </div>
        {orders.length === 0 ? (
          <p className="text-gray-500 text-sm">No orders yet. Export and submit your first board above.</p>
        ) : (
          <table className="w-full text-sm">
            <thead><tr className="border-b border-gray-800 text-gray-500 text-xs">
              <th className="text-left py-2">Board</th><th className="text-left py-2">Ref</th><th className="text-left py-2">House</th><th className="text-left py-2">Qty</th><th className="text-left py-2">Status</th><th className="text-left py-2">Date</th>
            </tr></thead>
            <tbody>
              {orders.map((o) => (
                <tr key={o.id} className="border-b border-gray-800/50">
                  <td className="py-2">{o.board_name}</td>
                  <td className="py-2 text-gray-400 font-mono text-xs">{o.order_ref}</td>
                  <td className="py-2 text-xs uppercase">{o.fab_house}</td>
                  <td className="py-2">{o.quantity}</td>
                  <td className="py-2"><span className={`text-xs px-1.5 py-0.5 rounded ${o.status === 'pending' ? 'bg-amber-900/50 text-amber-300' : 'bg-emerald-900/50 text-emerald-300'}`}>{o.status}</span></td>
                  <td className="py-2 text-xs text-gray-400">{o.created_at?.slice(0, 10)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
