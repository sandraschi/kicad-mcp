import { useState, useEffect } from 'react';
import { apiPost, apiGet } from '../lib/api';
import PcbViewer from '../components/PcbViewer';

interface DemoStep {
  id: string;
  label: string;
  description: string;
  icon: string;
  run: () => Promise<string>;
  result?: string;
  status: 'idle' | 'running' | 'done' | 'error';
}

const DEMO_FILES = {
  pcb: 'complex_hierarchy.kicad_pcb',
  sch: 'complex_hierarchy.kicad_sch',
};

export default function DemoPage() {
  const [glbUrl, setGlbUrl] = useState('');
  const [serverOk, setServerOk] = useState<boolean | null>(null);

  useEffect(() => {
    apiGet('/api/v1/status').then((s) => setServerOk(s.kicad_available)).catch(() => setServerOk(false));
  }, []);

  const [steps, setSteps] = useState<DemoStep[]>([
    {
      id: 'status',
      label: 'System Status',
      description: 'Check KiCad availability, version, and bridge mode',
      icon: '🔌',
      status: 'idle',
      run: async () => {
        const r = await apiGet('/api/v1/status');
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'board-info',
      label: 'Board Inspection',
      description: 'Load the demo PCB and extract metadata (layers, components, nets, tracks)',
      icon: '📊',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/pcb_info', { file_name: DEMO_FILES.pcb });
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'drc',
      label: 'Design Rule Check',
      description: 'Run DRC on the 10-layer demo board — checks clearance, annulus, and fab constraints',
      icon: '✅',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/pcb_drc', { file_name: DEMO_FILES.pcb, severity: 'error' });
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'components',
      label: 'Component Inventory',
      description: 'List all placed components with reference, value, footprint, and position',
      icon: '🔩',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/pcb_list_components', { file_name: DEMO_FILES.pcb });
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'bom',
      label: 'Bill of Materials',
      description: 'Generate a grouped BOM from the schematic — value, quantity, references',
      icon: '📦',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/bom_generate', { file_name: DEMO_FILES.sch, output_format: 'grouped_json', group_by: 'value' });
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'erc',
      label: 'Electrical Rules Check',
      description: 'Check schematic for unconnected pins, power issues, and ERC violations',
      icon: '⚡',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/sch_erc', { file_name: DEMO_FILES.sch });
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'glb',
      label: '3D View',
      description: 'Export the board as GLB and open the interactive 3D viewer',
      icon: '🌐',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/pcb_export_glb', { file_name: DEMO_FILES.pcb, output_name: 'demo_3d.glb' });
        if (r.success) setGlbUrl(`/api/v1/download/demo_3d.glb?dir=outputs&t=${Date.now()}`);
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'nets',
      label: 'Net Analysis',
      description: 'List all nets with pad connections — shows signal routing complexity',
      icon: '🔗',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/pcb_list_nets', { file_name: DEMO_FILES.pcb });
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'gerber',
      label: 'Fabrication Export',
      description: 'Export full Gerber + drill files — ready to send to a PCB fab house',
      icon: '🏭',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/pcb_export_gerber', { file_name: DEMO_FILES.pcb, output_dir_name: 'demo_gerber' });
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'pos',
      label: 'Pick & Place',
      description: 'Export assembly positions for automated pick-and-place machines',
      icon: '🤖',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/pcb_export_pos', { file_name: DEMO_FILES.pcb });
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'step',
      label: 'STEP 3D Model',
      description: 'Export STEP for mechanical CAD — enclosure design in FreeCAD',
      icon: '📐',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/pcb_export_step', { file_name: DEMO_FILES.pcb, output_name: 'demo_3d.step' });
        return JSON.stringify(r, null, 2);
      },
    },
    {
      id: 'ipc2581',
      label: 'IPC-2581 Fabrication',
      description: 'Export in IPC-2581 industry standard format',
      icon: '📋',
      status: 'idle',
      run: async () => {
        const r = await apiPost('/api/v1/control/pcb_export_ipc2581', { file_name: DEMO_FILES.pcb });
        return JSON.stringify(r, null, 2);
      },
    },
  ]);

  const [activeResult, setActiveResult] = useState<string | null>(null);
  const [runningAll, setRunningAll] = useState(false);

  const runStep = async (idx: number) => {
    setSteps((prev) => {
      const next = [...prev];
      next[idx] = { ...next[idx], status: 'running' };
      return next;
    });
    setActiveResult(null);
    try {
      const step = steps[idx];
      const result = await step.run();
      setActiveResult(result);
      setSteps((prev) => {
        const next = [...prev];
        next[idx] = { ...next[idx], status: 'done', result };
        return next;
      });
    } catch (e) {
      setActiveResult(String(e));
      setSteps((prev) => {
        const next = [...prev];
        next[idx] = { ...next[idx], status: 'error' };
        return next;
      });
    }
  };

  const runAll = async () => {
    setRunningAll(true);
    for (let i = 0; i < steps.length; i++) {
      await runStep(i);
    }
    setRunningAll(false);
  };

  const statusIcon = (s: string) => {
    switch (s) {
      case 'running': return <span className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin inline-block" />;
      case 'done': return <span className="text-emerald-400">✓</span>;
      case 'error': return <span className="text-red-400">✕</span>;
      default: return <span className="text-gray-500">▸</span>;
    }
  };

  if (serverOk === null) {
    return <div className="flex items-center justify-center h-64 text-gray-400"><div className="w-6 h-6 border-2 border-blue-500 border-t-transparent rounded-full animate-spin mr-3" />Connecting to server...</div>;
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Demo: complex_hierarchy</h1>
          <p className="text-gray-400 text-sm mt-1">
            KiCad 10.0 demo project — {serverOk ? 'KiCad CLI detected ✓' : 'KiCad not available ✕'}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={runAll}
            disabled={runningAll || !serverOk}
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-500 hover:to-purple-500 rounded-lg text-sm font-semibold disabled:opacity-50 transition-all"
          >
            {runningAll ? 'Running All...' : '▶ Run Full Demo'}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mb-6">
        {steps.map((step, i) => (
          <button
            key={step.id}
            onClick={() => runStep(i)}
            disabled={runningAll || step.status === 'running' || !serverOk}
            className={`text-left bg-gray-900 border rounded-lg p-3 transition-all hover:bg-gray-800 disabled:opacity-50 ${
              step.status === 'done' ? 'border-emerald-700/50' : step.status === 'error' ? 'border-red-700/50' : 'border-gray-800'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="text-lg">{step.icon}</span>
              {statusIcon(step.status)}
            </div>
            <div className="text-sm font-medium">{step.label}</div>
            <div className="text-xs text-gray-500 mt-0.5">{step.description}</div>
          </button>
        ))}
      </div>

      {activeResult && (
        <div className="bg-gray-900 border border-gray-800 rounded-lg">
          <div className="flex items-center justify-between px-4 py-2 border-b border-gray-800">
            <span className="text-xs text-gray-400 font-mono">Response</span>
            <button onClick={() => setActiveResult(null)} className="text-gray-500 hover:text-gray-300 text-xs">Close</button>
          </div>
          <pre className="p-4 text-xs overflow-auto max-h-80 font-mono leading-relaxed">{activeResult}</pre>
        </div>
      )}

      {glbUrl && <PcbViewer glbUrl={glbUrl} onClose={() => setGlbUrl('')} />}
    </div>
  );
}
