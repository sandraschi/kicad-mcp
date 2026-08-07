import { Route, Routes } from "react-router-dom";
import AppLayout from "./components/AppLayout";
import BoardsPage from "./pages/BoardsPage";
import BomPage from "./pages/BomPage";
import ChatPage from "./pages/ChatPage";
import Dashboard from "./pages/Dashboard";
import DemoPage from "./pages/DemoPage";
import FabPage from "./pages/FabPage";
import FilesPage from "./pages/FilesPage";
import LibraryPage from "./pages/LibraryPage";
import MarketplacePage from "./pages/MarketplacePage";
import PcbPage from "./pages/PcbPage";
import ReviewPage from "./pages/ReviewPage";
import ReviewsPage from "./pages/ReviewsPage";
import SchematicPage from "./pages/SchematicPage";
import StatusPage from "./pages/StatusPage";

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
        <Route path="/reviews" element={<ReviewsPage />} />
        <Route path="/review/:id" element={<ReviewPage />} />
        <Route path="/boards" element={<BoardsPage />} />
      </Routes>
    </AppLayout>
  );
}
