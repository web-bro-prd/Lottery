import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/Sidebar';
import DashboardPage from './pages/DashboardPage';
import DrawsPage from './pages/DrawsPage';
import StatsPage from './pages/StatsPage';
import TrendPage from './pages/TrendPage';
import SimulatePage from './pages/SimulatePage';
import BacktestPage from './pages/BacktestPage';
import PatternAnalysisPage from './pages/PatternAnalysisPage';
import RecommendPage from './pages/RecommendPage';
import CollectPage from './pages/CollectPage';
import WeeklyHistoryPage from './pages/WeeklyHistoryPage';
import PensionDashboardPage from './pages/PensionDashboardPage';
import PensionDrawsPage from './pages/PensionDrawsPage';
import PensionStatsPage from './pages/PensionStatsPage';
import PensionRecommendPage from './pages/PensionRecommendPage';
import PensionCollectPage from './pages/PensionCollectPage';
import PensionWeeklyHistoryPage from './pages/PensionWeeklyHistoryPage';
import './App.css';

export default function App() {
  return (
    <BrowserRouter>
      <div className="app-layout">
        <Sidebar />
        <main className="app-main">
          <Routes>
            <Route path="/" element={<Navigate to="/dashboard" replace />} />
            {/* 로또 */}
            <Route path="/weekly-history"  element={<WeeklyHistoryPage />} />
            <Route path="/dashboard"       element={<DashboardPage />} />
            <Route path="/draws"           element={<DrawsPage />} />
            <Route path="/stats"           element={<StatsPage />} />
            <Route path="/trend"           element={<TrendPage />} />
            <Route path="/simulate"        element={<SimulatePage />} />
            <Route path="/backtest"        element={<BacktestPage />} />
            <Route path="/pattern"         element={<PatternAnalysisPage />} />
            <Route path="/recommend"       element={<RecommendPage />} />
            <Route path="/collect"         element={<CollectPage />} />
            {/* 연금복권 */}
            <Route path="/pension/weekly-history" element={<PensionWeeklyHistoryPage />} />
            <Route path="/pension/dashboard"      element={<PensionDashboardPage />} />
            <Route path="/pension/draws"          element={<PensionDrawsPage />} />
            <Route path="/pension/stats"          element={<PensionStatsPage />} />
            <Route path="/pension/recommend"      element={<PensionRecommendPage />} />
            <Route path="/pension/collect"        element={<PensionCollectPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
