import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import './Sidebar.css';

const menus = [
  { path: '/dashboard', label: '대시보드',   icon: '🏠' },
  { path: '/draws',     label: '당첨 번호',   icon: '🎯' },
  { path: '/stats',     label: '통계 분석',   icon: '📊' },
  { path: '/trend',     label: '트렌드',      icon: '📈' },
  { path: '/simulate',  label: '시뮬레이션',  icon: '🔁' },
  { path: '/backtest',  label: '백테스팅',    icon: '🧪' },
  { path: '/pattern',   label: '패턴 분석',   icon: '🔬' },
  { path: '/recommend', label: '번호 추천',   icon: '✨' },
  { path: '/collect',   label: '데이터 수집', icon: '⬇️' },
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);
  const location = useLocation();

  // 페이지 이동 시 자동으로 닫기
  useEffect(() => {
    setOpen(false);
  }, [location.pathname]);

  return (
    <>
      {/* 모바일 상단 바 */}
      <div className="mobile-topbar">
        <button className="hamburger" onClick={() => setOpen(o => !o)} aria-label="메뉴">
          <span /><span /><span />
        </button>
        <span className="mobile-logo">🎰 로또 분석</span>
      </div>

      {/* 사이드바 오버레이 (모바일) */}
      {open && <div className="sidebar-overlay" onClick={() => setOpen(false)} />}

      {/* 사이드바 본체 */}
      <nav className={`sidebar ${open ? 'open' : ''}`}>
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
    </>
  );
}
