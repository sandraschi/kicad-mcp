import { useState } from 'react';
import { NavLink } from 'react-router-dom';
import { Activity, CircuitBoard, Cpu, FileText, FolderOpen, Library, ShoppingBag } from 'lucide-react';

const navItems = [
  { to: '/', label: 'Dashboard', icon: Activity },
  { to: '/pcb', label: 'PCB', icon: CircuitBoard },
  { to: '/schematic', label: 'Schematic', icon: Cpu },
  { to: '/bom', label: 'BOM', icon: FileText },
  { to: '/library', label: 'Library', icon: Library },
  { to: '/marketplace', label: 'Market', icon: ShoppingBag },
  { to: '/files', label: 'Files', icon: FolderOpen },
  { to: '/status', label: 'Status', icon: Activity },
];

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="flex h-screen">
      <aside className={`bg-gray-900 border-r border-gray-800 transition-all ${collapsed ? 'w-14' : 'w-56'}`}>
        <div className="p-3 border-b border-gray-800 flex items-center gap-2">
          <CircuitBoard size={20} className="text-emerald-400 shrink-0" />
          {!collapsed && <span className="font-semibold text-sm">KiCad MCP</span>}
        </div>
        <button
          className="w-full p-2 text-xs text-gray-500 hover:text-gray-300 border-b border-gray-800"
          onClick={() => setCollapsed(!collapsed)}
        >
          {collapsed ? '>' : '<'}
        </button>
        <nav className="p-2 space-y-1">
          {navItems.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-2 px-2 py-2 rounded text-sm transition ${
                  isActive ? 'bg-emerald-900/40 text-emerald-300' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800'
                }`
              }
            >
              <Icon size={16} className="shrink-0" />
              {!collapsed && <span>{label}</span>}
            </NavLink>
          ))}
        </nav>
      </aside>
      <main className="flex-1 overflow-auto p-6">{children}</main>
    </div>
  );
}
