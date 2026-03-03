import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import DrawsPage from './pages/DrawsPage';
import StatsPage from './pages/StatsPage';
import TrendPage from './pages/TrendPage';
import SimulatePage from './pages/SimulatePage';
import RecommendPage from './pages/RecommendPage';
import CollectPage from './pages/CollectPage';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/draws" element={<DrawsPage />} />
            <Route path="/stats" element={<StatsPage />} />
            <Route path="/trend" element={<TrendPage />} />
            <Route path="/simulate" element={<SimulatePage />} />
            <Route path="/recommend" element={<RecommendPage />} />
            <Route path="/collect" element={<CollectPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
