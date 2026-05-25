import { useState } from 'react';
import { apiPost, apiGet } from '../lib/api';
import PcbViewer from '../components/PcbViewer';

export default function PcbPage() {
  const [fileName, setFileName] = useState('');
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [loading, setLoading] = useState(false);
  const [glbUrl, setGlbUrl] = useState('');
  const [svgUrl, setSvgUrl] = useState('');

  const runTool = async (tool: string, args: Record<string, unknown> = {}) => {
    setLoading(true);
    setResult(null);
    try {
      const res = await apiPost(`/api/v1/control/${tool}`, { file_name: fileName, ...args });
      setResult(res);
    } catch (e) {
      setResult({ error: String(e) });
    }
    setLoading(false);
  };

  const exportAndViewGlb = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await apiPost('/api/v1/control/pcb_export_glb', { file_name: fileName, output_name: 'preview.glb' });
      setResult(res);
      if (res.success) {
        setGlbUrl(`/api/v1/download/preview.glb?dir=outputs&t=${Date.now()}`);
      }
    } catch (e) {
      setResult({ error: String(e) });
    }
    setLoading(false);
  };

  const exportAndViewSvg = async () => {
    setLoading(true);
    setResult(null);
    try {
      const res = await apiPost('/api/v1/control/pcb_export_svg', { file_name: fileName, output_name: 'preview.svg' });
      setResult(res);
      if (res.success) {
        setSvgUrl(`/api/v1/download/preview.svg?dir=outputs&t=${Date.now()}`);
      }
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
        <button className="px-3 py-2 bg-blue-800 hover:bg-blue-700 border border-blue-600 rounded text-sm disabled:opacity-50" disabled={!fileName || loading} onClick={exportAndViewGlb}>
          3D View (GLB)
        </button>
        <button className="px-3 py-2 bg-green-800 hover:bg-green-700 border border-green-600 rounded text-sm disabled:opacity-50" disabled={!fileName || loading} onClick={exportAndViewSvg}>
          SVG View
        </button>
        {[
          { label: 'Board Info', tool: 'pcb_info' },
          { label: 'List Components', tool: 'pcb_list_components' },
          { label: 'List Nets', tool: 'pcb_list_nets' },
          { label: 'List Tracks', tool: 'pcb_list_tracks' },
          { label: 'DRC Check', tool: 'pcb_drc' },
          { label: 'Export STEP', tool: 'pcb_export_step' },
          { label: 'Export Gerber', tool: 'pcb_export_gerber' },
          { label: 'Export POS', tool: 'pcb_export_pos' },
          { label: 'Export DXF', tool: 'pcb_export_dxf' },
          { label: 'Export PDF', tool: 'pcb_export_pdf' },
          { label: 'Export VRML', tool: 'pcb_export_vrml' },
          { label: 'Export IPC-2581', tool: 'pcb_export_ipc2581' },
          { label: 'Export ODB++', tool: 'pcb_export_odbpp' },
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

      {glbUrl && <PcbViewer glbUrl={glbUrl} onClose={() => setGlbUrl('')} />}
      {svgUrl && (
        <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center" onClick={() => setSvgUrl('')}>
          <div className="relative w-[90vw] h-[85vh] bg-white rounded-xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <button onClick={() => setSvgUrl('')} className="absolute top-3 right-3 z-10 bg-gray-200 hover:bg-gray-300 rounded-lg w-8 h-8 flex items-center justify-center text-gray-700 font-bold">
              ✕
            </button>
            <img src={svgUrl} alt="PCB SVG" className="w-full h-full object-contain p-4" />
          </div>
        </div>
      )}
    </div>
  );
}
