import { Routes, Route } from 'react-router-dom';
import AppLayout from './components/AppLayout';
import Dashboard from './pages/Dashboard';
import PcbPage from './pages/PcbPage';
import SchematicPage from './pages/SchematicPage';
import BomPage from './pages/BomPage';
import LibraryPage from './pages/LibraryPage';
import MarketplacePage from './pages/MarketplacePage';
import FilesPage from './pages/FilesPage';
import DemoPage from './pages/DemoPage';
import StatusPage from './pages/StatusPage';
import ChatPage from './pages/ChatPage';
import FabPage from './pages/FabPage';

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
        <Route path="/demo" element={<DemoPage />} />
        <Route path="/status" element={<StatusPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/fab" element={<FabPage />} />
      </Routes>
    </AppLayout>
  );
}
