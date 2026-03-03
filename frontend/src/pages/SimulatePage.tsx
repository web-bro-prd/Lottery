import { useState } from 'react';
import { simulateRandom, simulateMonteCarlo } from '../api/lottery';
import type { SimulateResult, MonteCarloResult } from '../types';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import './SimulatePage.css';

export default function SimulatePage() {
  const [tab, setTab] = useState<'random' | 'montecarlo'>('random');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Random sim
  const [gamesPerRound, setGamesPerRound] = useState(5);
  const [randomResult, setRandomResult] = useState<SimulateResult | null>(null);

  // Monte carlo
  const [mcGames, setMcGames] = useState(1000);
  const [mcTrials, setMcTrials] = useState(10);
  const [mcResult, setMcResult] = useState<MonteCarloResult | null>(null);

  const runRandom = async () => {
    setLoading(true);
    setError('');
    try {
      const r = await simulateRandom({ games_per_round: gamesPerRound });
      setRandomResult(r);
    } catch {
      setError('시뮬레이션 실패. 데이터를 먼저 수집하세요.');
    } finally {
      setLoading(false);
    }
  };

  const runMonteCarlo = async () => {
    setLoading(true);
    setError('');
    try {
      const r = await simulateMonteCarlo({ games: mcGames, trials: mcTrials });
      setMcResult(r);
    } catch {
      setError('시뮬레이션 실패');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="simulate-page">
      <h1 className="page-title">시뮬레이션</h1>

      <div className="tab-bar">
        <button className={tab === 'random' ? 'active' : ''} onClick={() => setTab('random')}>랜덤 구매 시뮬</button>
        <button className={tab === 'montecarlo' ? 'active' : ''} onClick={() => setTab('montecarlo')}>몬테카를로</button>
      </div>

      {error && <div className="error-msg">{error}</div>}

      {tab === 'random' && (
        <div>
          <section className="section">
            <h2 className="section-title">랜덤 구매 시뮬레이션</h2>
            <p className="section-desc">
              역대 모든 회차에 매회 N게임씩 완전 랜덤으로 구매했을 때의 수익률을 계산합니다.
            </p>
            <div className="config-row">
              <label>
                회차당 게임 수
                <input type="number" min={1} max={20} value={gamesPerRound}
                  onChange={e => setGamesPerRound(Number(e.target.value))} />
              </label>
              <button className="btn-primary" onClick={runRandom} disabled={loading}>
                {loading ? '실행 중...' : '시뮬레이션 실행'}
              </button>
            </div>
          </section>

          {randomResult && (
            <div className="result-area">
              <div className="stat-cards">
                <div className="stat-card">
                  <div className="stat-label">총 지출</div>
                  <div className="stat-value">{randomResult.total_spent.toLocaleString()}원</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">총 당첨금</div>
                  <div className="stat-value">{randomResult.total_prize.toLocaleString()}원</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">순손익</div>
                  <div className={`stat-value ${randomResult.net >= 0 ? 'positive' : 'negative'}`}>
                    {randomResult.net.toLocaleString()}원
                  </div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">ROI</div>
                  <div className={`stat-value ${randomResult.roi >= 0 ? 'positive' : 'negative'}`}>
                    {randomResult.roi}%
                  </div>
                </div>
              </div>

              <section className="section">
                <h2 className="section-title">등수별 당첨 횟수</h2>
                <div className="rank-summary">
                  {Object.entries(randomResult.rank_summary).map(([rank, count]) => (
                    <div key={rank} className="rank-item">
                      <span className="rank-label">{rank === '0' ? '미당첨' : `${rank}등`}</span>
                      <span className="rank-count">{count.toLocaleString()}회</span>
                    </div>
                  ))}
                </div>
              </section>
            </div>
          )}
        </div>
      )}

      {tab === 'montecarlo' && (
        <div>
          <section className="section">
            <h2 className="section-title">몬테카를로 시뮬레이션</h2>
            <p className="section-desc">
              가상의 번호로 N게임을 M번 반복하여 ROI 분포를 확인합니다.
            </p>
            <div className="config-row">
              <label>
                게임 수
                <input type="number" min={100} max={100000} value={mcGames}
                  onChange={e => setMcGames(Number(e.target.value))} />
              </label>
              <label>
                반복 횟수
                <input type="number" min={1} max={100} value={mcTrials}
                  onChange={e => setMcTrials(Number(e.target.value))} />
              </label>
              <button className="btn-primary" onClick={runMonteCarlo} disabled={loading}>
                {loading ? '실행 중...' : '시뮬레이션 실행'}
              </button>
            </div>
          </section>

          {mcResult && (
            <div className="result-area">
              <div className="stat-cards">
                <div className="stat-card">
                  <div className="stat-label">평균 ROI</div>
                  <div className="stat-value negative">{mcResult.avg_roi}%</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">최소 ROI</div>
                  <div className="stat-value negative">{mcResult.min_roi}%</div>
                </div>
                <div className="stat-card">
                  <div className="stat-label">최대 ROI</div>
                  <div className={`stat-value ${mcResult.max_roi >= 0 ? 'positive' : 'negative'}`}>
                    {mcResult.max_roi}%
                  </div>
                </div>
              </div>

              <section className="section">
                <h2 className="section-title">ROI 분포</h2>
                <ResponsiveContainer width="100%" height={250}>
                  <BarChart
                    data={mcResult.roi_distribution.map((roi, i) => ({ trial: i + 1, roi }))}
                  >
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="trial" tick={{ fontSize: 11 }} label={{ value: '시도', position: 'insideBottom', offset: -2 }} />
                    <YAxis tick={{ fontSize: 11 }} unit="%" />
                    <Tooltip formatter={(v: number) => [`${v}%`, 'ROI']} />
                    <Bar dataKey="roi" fill="#4a90d9" name="ROI" />
                  </BarChart>
                </ResponsiveContainer>
              </section>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
