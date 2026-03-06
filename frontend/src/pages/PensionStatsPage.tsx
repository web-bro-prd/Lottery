import { useEffect, useState } from 'react';
import { fetchPensionStats } from '../api/lottery';
import './PensionStatsPage.css';

// 실제 API 응답 타입 (백엔드 구조에 맞게)
interface RawPensionStats {
  total_draws: number;
  latest_round: number;
  latest_date: string;
  digit_frequency: Record<string, Record<string, { count: number; pct: number }>>;
  group_distribution: Record<string, number>;
  hot_cold: Record<string, { hot: { digit: string; recent_pct: number; all_pct: number; diff: number }[]; cold: { digit: string; recent_pct: number; all_pct: number; diff: number }[] }>;
  odd_even: Record<string, number>;
  sum_distribution: { average: number; min: number; max: number; buckets?: Record<string, number> };
}

const POS_LABELS = ['1자리', '2자리', '3자리', '4자리', '5자리', '6자리'];
const POS_KEYS = ['d1', 'd2', 'd3', 'd4', 'd5', 'd6'];

export default function PensionStatsPage() {
  const [stats, setStats] = useState<RawPensionStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPensionStats()
      .then(data => setStats(data as unknown as RawPensionStats))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">불러오는 중...</div>;
  if (error || !stats) return <div className="page-error">{error ?? '데이터 없음'}</div>;

  return (
    <div className="pension-stats-page">
      <h1 className="page-title">연금복권 통계 분석</h1>
      <div className="stats-meta">총 {stats.total_draws}회차 | 최신 {stats.latest_round}회 ({stats.latest_date})</div>

      {/* 조 분포 */}
      <section className="section">
        <h2 className="section-title">조(組) 분포</h2>
        <div className="grp-bars">
          {Object.entries(stats.group_distribution)
            .sort(([a], [b]) => Number(a) - Number(b))
            .map(([grp, cnt]) => {
              const pct = Math.round(cnt / stats.total_draws * 100);
              return (
                <div className="grp-bar-row" key={grp}>
                  <span className="grp-label">{grp}조</span>
                  <div className="grp-bar-bg">
                    <div className="grp-bar-fill" style={{ width: `${Math.min(pct * 4, 100)}%` }} />
                  </div>
                  <span className="grp-count">{cnt}회 ({pct}%)</span>
                </div>
              );
            })}
        </div>
      </section>

      {/* 자릿수별 빈도 */}
      <section className="section">
        <h2 className="section-title">자릿수별 숫자 빈도 (상위 5개)</h2>
        <div className="digit-freq-grid">
          {POS_KEYS.map((key, posIdx) => {
            const posData = stats.digit_frequency[key] ?? {};
            const sorted = Object.entries(posData)
              .map(([digit, v]) => ({ digit, ...v }))
              .sort((a, b) => b.count - a.count)
              .slice(0, 5);
            return (
              <div className="digit-freq-pos" key={key}>
                <div className="digit-freq-pos-label">{POS_LABELS[posIdx]}</div>
                {sorted.map(item => (
                  <div className="digit-freq-row" key={item.digit}>
                    <span className="digit-label">{item.digit}</span>
                    <div className="digit-bar-bg">
                      <div className="digit-bar-fill" style={{ width: `${Math.min(item.pct * 5, 100)}%` }} />
                    </div>
                    <span className="digit-pct">{item.pct.toFixed(1)}%</span>
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </section>

      {/* 핫/콜드 by 자리 */}
      <section className="section">
        <h2 className="section-title">자릿수별 HOT / COLD</h2>
        <div className="hot-cold-grid">
          {POS_KEYS.map((key, posIdx) => {
            const hc = stats.hot_cold[key];
            if (!hc) return null;
            return (
              <div className="hot-cold-pos" key={key}>
                <div className="hot-cold-pos-label">{POS_LABELS[posIdx]}</div>
                <div className="hot-cold-row">
                  <span className="hc-title hot-title">HOT</span>
                  {hc.hot.map(d => (
                    <span className="hot-badge" key={d.digit}>{d.digit}</span>
                  ))}
                </div>
                <div className="hot-cold-row">
                  <span className="hc-title cold-title">COLD</span>
                  {hc.cold.map(d => (
                    <span className="cold-badge" key={d.digit}>{d.digit}</span>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* 합계 분포 */}
      <section className="section">
        <h2 className="section-title">번호 합계 분포</h2>
        <div className="sum-info">
          평균: <strong>{stats.sum_distribution.average.toFixed(1)}</strong> &nbsp;|&nbsp;
          최소: <strong>{stats.sum_distribution.min}</strong> &nbsp;|&nbsp;
          최대: <strong>{stats.sum_distribution.max}</strong>
        </div>
      </section>
    </div>
  );
}
