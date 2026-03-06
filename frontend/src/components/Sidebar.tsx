import { useState, useEffect } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import './Sidebar.css';

const lottoMenus = [
  { path: '/weekly-history',  label: '이번 주 추천번호', icon: '🏆' },
  { path: '/dashboard',       label: '대시보드',          icon: '🏠' },
  { path: '/draws',           label: '당첨 번호',         icon: '🎯' },
  { path: '/stats',           label: '통계 분석',         icon: '📊' },
  { path: '/trend',           label: '트렌드',            icon: '📈' },
  { path: '/simulate',        label: '시뮬레이션',        icon: '🔁' },
  { path: '/backtest',        label: '백테스팅',          icon: '🧪' },
  { path: '/pattern',         label: '패턴 분석',         icon: '🔬' },
  { path: '/recommend',       label: '번호 추천',         icon: '✨' },
  { path: '/collect',         label: '데이터 수집',       icon: '⬇️' },
];

const pensionMenus = [
  { path: '/pension/weekly-history', label: '이번 주 추천번호', icon: '🏆' },
  { path: '/pension/dashboard',      label: '대시보드',          icon: '🏠' },
  { path: '/pension/draws',          label: '당첨 번호',         icon: '🎯' },
  { path: '/pension/stats',          label: '통계 분석',         icon: '📊' },
  { path: '/pension/recommend',      label: '번호 추천',         icon: '✨' },
  { path: '/pension/collect',        label: '데이터 수집',       icon: '⬇️' },
];

export default function Sidebar() {
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState<'lotto' | 'pension'>('lotto');
  const location = useLocation();

  // 페이지 이동 시 자동으로 닫기 + 섹션 자동 감지
  useEffect(() => {
    setOpen(false);
    if (location.pathname.startsWith('/pension')) {
      setSection('pension');
    } else {
      setSection('lotto');
    }
  }, [location.pathname]);

  const menus = section === 'lotto' ? lottoMenus : pensionMenus;

  return (
    <>
      {/* 모바일 상단 바 */}
      <div className="mobile-topbar">
        <button className="hamburger" onClick={() => setOpen(o => !o)} aria-label="메뉴">
          <span /><span /><span />
        </button>
        <span className="mobile-logo">
          {section === 'pension' ? '💰 연금복권' : '🎰 로또 분석'}
        </span>
      </div>

      {/* 사이드바 오버레이 (모바일) */}
      {open && <div className="sidebar-overlay" onClick={() => setOpen(false)} />}

      {/* 사이드바 본체 */}
      <nav className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-logo">
          <span className="logo-icon">{section === 'pension' ? '💰' : '🎰'}</span>
          <span className="logo-text">{section === 'pension' ? '연금복권720+' : '로또 분석'}</span>
        </div>

        {/* 탭 전환 */}
        <div className="sidebar-tabs">
          <button
            className={`sidebar-tab ${section === 'lotto' ? 'active' : ''}`}
            onClick={() => setSection('lotto')}
          >
            로또
          </button>
          <button
            className={`sidebar-tab ${section === 'pension' ? 'active' : ''}`}
            onClick={() => setSection('pension')}
          >
            연금복권
          </button>
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
