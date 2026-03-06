import { useEffect, useState } from 'react';
import { fetchPensionStatus, fetchPensionLatestDraws } from '../api/lottery';
import type { PensionStatus, PensionDraw } from '../types';
import './PensionDashboardPage.css';

export default function PensionDashboardPage() {
  const [status, setStatus] = useState<PensionStatus | null>(null);
  const [latestDraws, setLatestDraws] = useState<PensionDraw[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchPensionStatus(), fetchPensionLatestDraws()])
      .then(([s, d]) => {
        setStatus(s);
        setLatestDraws([...d.draws].reverse());
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">불러오는 중...</div>;

  return (
    <div className="pension-dashboard-page">
      <h1 className="page-title">연금복권720+ 대시보드</h1>

      <div className="stat-cards">
        <div className="stat-card">
          <div className="stat-label">총 회차</div>
          <div className="stat-value">{status?.total_rounds?.toLocaleString() ?? '-'}회</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">최신 회차</div>
          <div className="stat-value">{status?.latest_round ?? '-'}회</div>
        </div>
        <div className="stat-card">
          <div className="stat-label">최근 추첨일</div>
          <div className="stat-value">{status?.latest_date ?? '-'}</div>
        </div>
      </div>

      <section className="section">
        <h2 className="section-title">최근 당첨 번호</h2>
        {latestDraws.length === 0 ? (
          <div className="empty-msg">데이터 없음. 데이터 수집을 먼저 진행하세요.</div>
        ) : (
          <div className="pension-draws-list">
            {latestDraws.map(d => (
              <div className="pension-draw-row" key={d.round}>
                <span className="pension-draw-round">{d.round}회</span>
                <span className="pension-draw-date">{d.draw_date}</span>
                <span className="pension-draw-grp">{d.grp}조</span>
                <span className="pension-draw-num">{String(d.num).padStart(6, '0')}</span>
                <span className="pension-draw-bonus-label">보너스</span>
                <span className="pension-draw-bonus">{String(d.bonus_num).padStart(6, '0')}</span>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
