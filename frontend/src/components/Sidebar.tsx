import { NavLink } from 'react-router-dom';
import './Sidebar.css';

const menus = [
  { path: '/dashboard', label: '대시보드', icon: '🏠' },
  { path: '/draws', label: '당첨 번호', icon: '🎯' },
  { path: '/stats', label: '통계 분석', icon: '📊' },
  { path: '/trend', label: '트렌드', icon: '📈' },
  { path: '/simulate', label: '시뮬레이션', icon: '🔁' },
  { path: '/backtest', label: '백테스팅', icon: '🧪' },
  { path: '/recommend', label: '번호 추천', icon: '✨' },
  { path: '/collect', label: '데이터 수집', icon: '⬇️' },
];

export default function Sidebar() {
  return (
    <nav className="sidebar">
      <div className="sidebar-logo">
        <span className="logo-icon">🎰</span>
        <span className="logo-text">로또 분석</span>
      </div>
      <ul className="sidebar-menu">
        {menus.map(m => (
          <li key={m.path}>
            <NavLink
              to={m.path}
              className={({ isActive }) => `menu-item ${isActive ? 'active' : ''}`}
            >
              <span className="menu-icon">{m.icon}</span>
              <span className="menu-label">{m.label}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
