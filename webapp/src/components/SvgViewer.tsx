import { useState } from 'react';

interface SvgViewerProps {
  svgUrl: string;
  onClose: () => void;
}

export default function SvgViewer({ svgUrl, onClose }: SvgViewerProps) {
  const [zoom, setZoom] = useState(1);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  return (
    <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center" onClick={onClose}>
      <div className="relative w-[90vw] h-[85vh] bg-white rounded-xl overflow-hidden" onClick={(e) => e.stopPropagation()}>
        <div className="absolute top-3 right-3 z-10 flex gap-2">
          <button
            onClick={() => setZoom((z) => Math.max(0.25, z - 0.25))}
            className="bg-gray-200 hover:bg-gray-300 rounded-lg w-8 h-8 flex items-center justify-center text-gray-700 font-bold"
          >
            −
          </button>
          <span className="bg-gray-200 rounded-lg px-2 h-8 flex items-center text-sm text-gray-600">
            {Math.round(zoom * 100)}%
          </span>
          <button
            onClick={() => setZoom((z) => Math.min(4, z + 0.25))}
            className="bg-gray-200 hover:bg-gray-300 rounded-lg w-8 h-8 flex items-center justify-center text-gray-700 font-bold"
          >
            +
          </button>
          <button
            onClick={onClose}
            className="bg-gray-200 hover:bg-gray-300 rounded-lg w-8 h-8 flex items-center justify-center text-gray-700 font-bold ml-2"
          >
            ✕
          </button>
        </div>

        <div className="w-full h-full flex items-center justify-center p-4 overflow-auto" style={{ cursor: 'grab' }}>
          {loading && (
            <div className="absolute inset-0 flex items-center justify-center text-gray-500 text-lg">
              <div className="flex flex-col items-center gap-3">
                <div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                Loading schematic...
              </div>
            </div>
          )}
          {error && (
            <div className="absolute inset-0 flex items-center justify-center text-red-500 text-lg">
              {error}
            </div>
          )}
          <img
            src={svgUrl}
            alt="Schematic"
            style={{
              transform: `scale(${zoom})`,
              transformOrigin: 'center center',
              maxWidth: '100%',
              maxHeight: '100%',
            }}
            onLoad={() => setLoading(false)}
            onError={() => {
              setLoading(false);
              setError('Failed to load SVG');
            }}
          />
        </div>
      </div>
    </div>
  );
}
