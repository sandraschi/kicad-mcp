import { useEffect, useState } from 'react';
import { apiGet, apiUpload } from '../lib/api';

export default function FilesPage() {
  const [files, setFiles] = useState<{ name: string; size_bytes: number }[]>([]);
  const [uploadMsg, setUploadMsg] = useState('');

  const refresh = () => {
    apiGet('/api/v1/list?dir=uploads').then((d) => setFiles(d.files || [])).catch(console.error);
  };

  useEffect(() => { refresh(); }, []);

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const res = await apiUpload(file);
      setUploadMsg(`Uploaded: ${res.filename}`);
      refresh();
    } catch (err) {
      setUploadMsg(`Error: ${err}`);
    }
  };

  return (
    <div>
      <h1 className="text-2xl font-bold mb-4">Files</h1>

      <label className="inline-block px-4 py-2 bg-emerald-700 hover:bg-emerald-600 rounded text-sm cursor-pointer mb-4">
        Upload KiCad File
        <input type="file" className="hidden" onChange={handleUpload} accept=".kicad_pcb,.kicad_sch,.kicad_pro,.kicad_mod,.kicad_sym,.lib,.pretty" />
      </label>

      {uploadMsg && <div className="text-sm text-gray-400 mb-4">{uploadMsg}</div>}

      <div className="bg-gray-900 border border-gray-800 rounded-lg">
        <div className="p-3 border-b border-gray-800 text-sm text-gray-400">
          Uploads ({files.length})
        </div>
        {files.length === 0 ? (
          <div className="p-4 text-sm text-gray-500">No files uploaded</div>
        ) : (
          files.map((f) => (
            <div key={f.name} className="flex justify-between px-4 py-2 border-b border-gray-800/50 text-sm">
              <span className="font-mono text-gray-300">{f.name}</span>
              <span className="text-gray-500">{(f.size_bytes / 1024).toFixed(1)} KB</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
