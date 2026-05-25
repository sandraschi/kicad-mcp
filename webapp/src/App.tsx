import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import Dashboard from './pages/Dashboard';
import PcbPage from './pages/PcbPage';
import SchematicPage from './pages/SchematicPage';
import BomPage from './pages/BomPage';
import LibraryPage from './pages/LibraryPage';
import MarketplacePage from './pages/MarketplacePage';
import FilesPage from './pages/FilesPage';
import StatusPage from './pages/StatusPage';

export default function App() {
  return (
    <AppLayout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/pcb" element={<PcbPage />} />
        <Route path="/schematic" element={<SchematicPage />} />
        <Route path="/bom" element={<BomPage />} />
        <Route path="/library" element={<LibraryPage />} />
        <Route path="/marketplace" element={<MarketplacePage />} />
        <Route path="/files" element={<FilesPage />} />
        <Route path="/status" element={<StatusPage />} />
      </Routes>
    </AppLayout>
  );
}
