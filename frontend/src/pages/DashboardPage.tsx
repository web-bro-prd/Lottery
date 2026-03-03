import { useEffect, useState } from 'react';
import { fetchStatus, fetchLatestDraws } from '../api/lottery';
import type { ServerStatus, DrawResult } from '../types';
import LottoBall from '../components/LottoBall';
import './DashboardPage.css';

export default function DashboardPage() {
  const [status, setStatus] = useState<ServerStatus | null>(null);
  const [latestDraws, setLatestDraws] = useState<DrawResult[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([fetchStatus(), fetchLatestDraws()])
      .then(([s, d]) => {
        setStatus(s);
        setLatestDraws(d.draws.reverse());
      })
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">불러오는 중...</div>;

  return (
    <div className="dashboard-page">
      <h1 className="page-title">대시보드</h1>

      {/* 요약 카드 */}
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

      {/* 최근 당첨 번호 */}
      <section className="section">
        <h2 className="section-title">최근 당첨 번호</h2>
        {latestDraws.length === 0 ? (
          <div className="empty-msg">
            데이터가 없습니다. <a href="/collect">데이터 수집</a>을 먼저 진행하세요.
          </div>
        ) : (
          <div className="draw-list">
            {latestDraws.map(draw => (
              <div key={draw.round} className="draw-row">
                <div className="draw-round">{draw.round}회</div>
                <div className="draw-date">{draw.draw_date}</div>
                <div className="draw-balls">
                  {[draw.num1, draw.num2, draw.num3, draw.num4, draw.num5, draw.num6].map(n => (
                    <LottoBall key={n} number={n} size="md" />
                  ))}
                  <span className="bonus-sep">+</span>
                  <LottoBall number={draw.bonus} bonus size="md" />
                </div>
                {draw.win1_prize && (
                  <div className="draw-prize">
                    1등: {Math.round(draw.win1_prize / 100_000_000).toLocaleString()}억원
                    ({draw.win1_count}명)
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
