import { useEffect, useState } from 'react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  PieChart, Pie, Cell, ResponsiveContainer,
} from 'recharts';
import { fetchStats } from '../api/lottery';
import type { FullStats } from '../types';
import './StatsPage.css';

const COLORS = ['#ffd700', '#4a90d9', '#e74c3c', '#7f8c8d', '#27ae60'];

export default function StatsPage() {
  const [stats, setStats] = useState<FullStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [tab, setTab] = useState<'frequency' | 'pattern' | 'pair'>('frequency');

  useEffect(() => {
    fetchStats()
      .then(setStats)
      .catch(() => setError('데이터를 불러올 수 없습니다. 먼저 데이터를 수집하세요.'))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">분석 중...</div>;
  if (error) return <div className="error-msg">{error}</div>;
  if (!stats) return null;

  // 빈도 차트 데이터
  const freqData = Array.from({ length: 45 }, (_, i) => ({
    num: i + 1,
    count: stats.frequency[String(i + 1)]?.count ?? 0,
    freq: stats.frequency[String(i + 1)]?.frequency ?? 0,
  }));

  // 홀짝 파이 데이터
  const oddEvenData = Object.entries(stats.odd_even.patterns).map(([k, v]) => ({
    name: k, value: v.count
  }));

  // 구간 데이터
  const zoneData = Object.entries(stats.zone.zone_frequency).map(([k, v]) => ({
    name: k, avg: v.avg_per_draw, share: v.share
  }));

  return (
    <div className="stats-page">
      <h1 className="page-title">통계 분석</h1>
      <div className="stats-summary">
        총 <strong>{stats.total_draws}</strong>회차 분석 |
        번호 합계 평균: <strong>{stats.sum_dist.average}</strong>
      </div>

      {/* 탭 */}
      <div className="tab-bar">
        <button className={tab === 'frequency' ? 'active' : ''} onClick={() => setTab('frequency')}>번호 빈도</button>
        <button className={tab === 'pattern' ? 'active' : ''} onClick={() => setTab('pattern')}>패턴 분석</button>
        <button className={tab === 'pair' ? 'active' : ''} onClick={() => setTab('pair')}>번호 조합</button>
      </div>

      {tab === 'frequency' && (
        <div className="tab-content">
          <section className="section">
            <h2 className="section-title">번호별 출현 빈도 (1~45)</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={freqData} margin={{ top: 5, right: 10, left: -10, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="num" tick={{ fontSize: 10 }} interval={4} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number, name: string) => [v, name === 'count' ? '출현수' : '빈도%']} />
                <Bar dataKey="count" fill="#4a90d9" name="출현수" />
              </BarChart>
            </ResponsiveContainer>
          </section>

          <div className="two-col">
            {/* TOP 10 */}
            <section className="section">
              <h2 className="section-title">자주 나온 번호 TOP 10</h2>
              <table className="rank-table">
                <thead><tr><th>순위</th><th>번호</th><th>출현</th><th>빈도</th></tr></thead>
                <tbody>
                  {Object.entries(stats.frequency)
                    .sort((a, b) => b[1].count - a[1].count)
                    .slice(0, 10)
                    .map(([num, info], i) => (
                      <tr key={num}>
                        <td>{i + 1}</td>
                        <td><span className={`num-badge color-${Math.ceil(Number(num) / 10)}`}>{num}</span></td>
                        <td>{info.count}</td>
                        <td>{info.frequency}%</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </section>

            {/* BOTTOM 10 */}
            <section className="section">
              <h2 className="section-title">덜 나온 번호 TOP 10</h2>
              <table className="rank-table">
                <thead><tr><th>순위</th><th>번호</th><th>출현</th><th>빈도</th></tr></thead>
                <tbody>
                  {Object.entries(stats.frequency)
                    .sort((a, b) => a[1].count - b[1].count)
                    .slice(0, 10)
                    .map(([num, info], i) => (
                      <tr key={num}>
                        <td>{i + 1}</td>
                        <td><span className={`num-badge color-${Math.ceil(Number(num) / 10)}`}>{num}</span></td>
                        <td>{info.count}</td>
                        <td>{info.frequency}%</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </section>
          </div>
        </div>
      )}

      {tab === 'pattern' && (
        <div className="tab-content">
          <div className="two-col">
            {/* 홀짝 분포 */}
            <section className="section">
              <h2 className="section-title">홀/짝 분포</h2>
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={oddEvenData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={80} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(1)}%`}>
                    {oddEvenData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </section>

            {/* 구간 분포 */}
            <section className="section">
              <h2 className="section-title">구간별 분포</h2>
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={zoneData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="avg" fill="#27ae60" name="회차당 평균" />
                </BarChart>
              </ResponsiveContainer>
            </section>
          </div>

          <section className="section">
            <h2 className="section-title">번호 합계 분포</h2>
            <div className="sum-info">
              평균 합계: <strong>{stats.sum_dist.average}</strong> |
              최소: <strong>{stats.sum_dist.min}</strong> |
              최대: <strong>{stats.sum_dist.max}</strong>
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={Object.entries(stats.sum_dist.buckets).map(([k, v]) => ({ range: k, count: v.count }))}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="count" fill="#e74c3c" name="회차 수" />
              </BarChart>
            </ResponsiveContainer>
          </section>
        </div>
      )}

      {tab === 'pair' && (
        <div className="tab-content">
          <div className="two-col">
            <section className="section">
              <h2 className="section-title">자주 나오는 번호 쌍 TOP 20</h2>
              <table className="rank-table">
                <thead><tr><th>순위</th><th>번호 쌍</th><th>출현</th><th>빈도</th></tr></thead>
                <tbody>
                  {stats.pair_frequency.map((p, i) => (
                    <tr key={i}>
                      <td>{i + 1}</td>
                      <td>{p.pair[0]} + {p.pair[1]}</td>
                      <td>{p.count}</td>
                      <td>{p.frequency}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="section">
              <h2 className="section-title">자주 나오는 3개 조합 TOP 10</h2>
              <table className="rank-table">
                <thead><tr><th>순위</th><th>번호 조합</th><th>출현</th><th>빈도</th></tr></thead>
                <tbody>
                  {stats.triple_frequency.map((t, i) => (
                    <tr key={i}>
                      <td>{i + 1}</td>
                      <td>{t.triple.join(' + ')}</td>
                      <td>{t.count}</td>
                      <td>{t.frequency}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
          </div>
        </div>
      )}
    </div>
  );
}
