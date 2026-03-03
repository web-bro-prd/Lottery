import { useEffect, useState } from 'react';
import { fetchTrend } from '../api/lottery';
import type { TrendAnalysis } from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ReferenceLine } from 'recharts';
import './TrendPage.css';

export default function TrendPage() {
  const [recentN, setRecentN] = useState(50);
  const [trend, setTrend] = useState<TrendAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const loadTrend = (n: number) => {
    setLoading(true);
    setError('');
    fetchTrend(n)
      .then(setTrend)
      .catch(() => setError('데이터를 불러올 수 없습니다. 먼저 데이터를 수집하세요.'))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadTrend(recentN); }, []);

  const hotData = trend?.hot_numbers.map(t => ({
    num: `${t.number}번`,
    diff: t.diff,
    all: t.all_frequency,
    recent: t.recent_frequency,
  })) ?? [];

  const coldData = trend?.cold_numbers.map(t => ({
    num: `${t.number}번`,
    diff: t.diff,
    all: t.all_frequency,
    recent: t.recent_frequency,
  })) ?? [];

  return (
    <div className="trend-page">
      <h1 className="page-title">트렌드 분석</h1>

      <section className="section">
        <div className="config-row">
          <label>
            최근 N회 기준
            <input
              type="number"
              min={10} max={200}
              value={recentN}
              onChange={e => setRecentN(Number(e.target.value))}
            />
          </label>
          <button className="btn-primary" onClick={() => loadTrend(recentN)} disabled={loading}>
            {loading ? '분석 중...' : '트렌드 분석'}
          </button>
        </div>
        {error && <div className="error-msg">{error}</div>}
      </section>

      {trend && (
        <>
          <div className="trend-desc">
            최근 {trend.recent_n}회 vs 전체 평균 빈도 차이 (+ 핫, - 콜드)
          </div>

          <div className="two-col">
            <section className="section">
              <h2 className="section-title hot">핫 번호 TOP 10 (최근 상승)</h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={hotData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fontSize: 11 }} unit="%" />
                  <YAxis type="category" dataKey="num" tick={{ fontSize: 11 }} width={40} />
                  <Tooltip formatter={(v: number) => [`${v}%`, '빈도 차이']} />
                  <ReferenceLine x={0} stroke="#666" />
                  <Bar dataKey="diff" fill="#e74c3c" name="빈도 차이" />
                </BarChart>
              </ResponsiveContainer>
            </section>

            <section className="section">
              <h2 className="section-title cold">콜드 번호 TOP 10 (최근 하락)</h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={coldData} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" tick={{ fontSize: 11 }} unit="%" />
                  <YAxis type="category" dataKey="num" tick={{ fontSize: 11 }} width={40} />
                  <Tooltip formatter={(v: number) => [`${v}%`, '빈도 차이']} />
                  <ReferenceLine x={0} stroke="#666" />
                  <Bar dataKey="diff" fill="#4a90d9" name="빈도 차이" />
                </BarChart>
              </ResponsiveContainer>
            </section>
          </div>

          <section className="section">
            <h2 className="section-title">상세 비교</h2>
            <div className="two-col">
              <table className="rank-table">
                <thead><tr><th>번호</th><th>전체 빈도</th><th>최근 빈도</th><th>차이</th></tr></thead>
                <tbody>
                  {trend.hot_numbers.map(t => (
                    <tr key={t.number}>
                      <td><span className="num-dot hot">{t.number}</span></td>
                      <td>{t.all_frequency}%</td>
                      <td>{t.recent_frequency}%</td>
                      <td className="positive">+{t.diff}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <table className="rank-table">
                <thead><tr><th>번호</th><th>전체 빈도</th><th>최근 빈도</th><th>차이</th></tr></thead>
                <tbody>
                  {trend.cold_numbers.map(t => (
                    <tr key={t.number}>
                      <td><span className="num-dot cold">{t.number}</span></td>
                      <td>{t.all_frequency}%</td>
                      <td>{t.recent_frequency}%</td>
                      <td className="negative">{t.diff}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
