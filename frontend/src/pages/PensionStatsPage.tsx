import { useEffect, useState } from 'react';
import { fetchPensionStats } from '../api/lottery';
import type { PensionStats } from '../types';
import './PensionStatsPage.css';

export default function PensionStatsPage() {
  const [stats, setStats] = useState<PensionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPensionStats()
      .then(setStats)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">불러오는 중...</div>;
  if (error || !stats) return <div className="page-error">{error ?? '데이터 없음'}</div>;

  const POS_LABELS = ['1번째', '2번째', '3번째', '4번째', '5번째', '6번째'];

  return (
    <div className="pension-stats-page">
      <h1 className="page-title">연금복권 통계 분석</h1>
      <div className="stats-meta">총 {stats.total_draws}회차 | 최신 {stats.latest_round}회</div>

      {/* 조 분포 */}
      <section className="section">
        <h2 className="section-title">조 분포</h2>
        <div className="grp-bars">
          {Object.entries(stats.group_distribution).sort(([a], [b]) => Number(a) - Number(b)).map(([grp, cnt]) => {
            const pct = Math.round(cnt / stats.total_draws * 100);
            return (
              <div className="grp-bar-row" key={grp}>
                <span className="grp-label">{grp}조</span>
                <div className="grp-bar-bg">
                  <div className="grp-bar-fill" style={{ width: `${Math.min(pct * 3, 100)}%` }} />
                </div>
                <span className="grp-count">{cnt}회 ({pct}%)</span>
              </div>
            );
          })}
        </div>
      </section>

      {/* 자릿수별 빈도 */}
      <section className="section">
        <h2 className="section-title">자릿수별 숫자 빈도 (0~9)</h2>
        <div className="digit-freq-grid">
          {stats.digit_frequency.map((posFreqs, posIdx) => (
            <div className="digit-freq-pos" key={posIdx}>
              <div className="digit-freq-pos-label">{POS_LABELS[posIdx]}자리</div>
              {[...posFreqs].sort((a, b) => b.count - a.count).slice(0, 5).map(item => (
                <div className="digit-freq-row" key={item.digit}>
                  <span className="digit-label">{item.digit}</span>
                  <div className="digit-bar-bg">
                    <div className="digit-bar-fill" style={{ width: `${item.pct * 5}%` }} />
                  </div>
                  <span className="digit-pct">{item.pct.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      {/* 핫/콜드 */}
      <section className="section two-col">
        <div>
          <h2 className="section-title">HOT 자릿수</h2>
          <div className="hot-cold-list">
            {stats.hot_digits.slice(0, 10).map((d, i) => (
              <span className="hot-badge" key={i}>{d.digit} <small>{d.pct.toFixed(1)}%</small></span>
            ))}
          </div>
        </div>
        <div>
          <h2 className="section-title">COLD 자릿수</h2>
          <div className="hot-cold-list">
            {stats.cold_digits.slice(0, 10).map((d, i) => (
              <span className="cold-badge" key={i}>{d.digit} <small>{d.pct.toFixed(1)}%</small></span>
            ))}
          </div>
        </div>
      </section>

      {/* 합계 분포 */}
      <section className="section">
        <h2 className="section-title">번호 합계 분포</h2>
        <div className="sum-info">
          평균: <strong>{stats.sum_distribution.average.toFixed(1)}</strong> &nbsp;
          최소: <strong>{stats.sum_distribution.min}</strong> &nbsp;
          최대: <strong>{stats.sum_distribution.max}</strong>
        </div>
      </section>
    </div>
  );
}
