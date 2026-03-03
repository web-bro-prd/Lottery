import { useState, useEffect } from 'react';
import {
  fetchBacktestStrategies,
  runBacktest,
  runBacktestCumulative,
  runBacktestSimulate,
} from '../api/lottery';
import type {
  StrategyInfo,
  BacktestResult,
  BacktestCumulativeResult,
  BacktestSimulateResult,
} from '../types';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, BarChart, Bar, Cell,
} from 'recharts';
import LottoBall from '../components/LottoBall';
import './BacktestPage.css';

const RANK_COLORS: Record<number, string> = {
  1: '#e74c3c', 2: '#e67e22', 3: '#f1c40f', 4: '#2ecc71', 5: '#3498db',
};
const LINE_COLORS = [
  '#e74c3c', '#3498db', '#2ecc71', '#f39c12',
  '#9b59b6', '#1abc9c', '#e67e22',
];

function formatWon(n: number): string {
  if (Math.abs(n) >= 100_000_000) return `${(n / 100_000_000).toFixed(1)}억`;
  if (Math.abs(n) >= 10_000) return `${Math.round(n / 10_000).toLocaleString()}만`;
  return n.toLocaleString();
}

export default function BacktestPage() {
  const [strategies, setStrategies] = useState<StrategyInfo[]>([]);

  // 설정
  const [window_, setWindow] = useState(50);
  const [games, setGames] = useState(5);
  const [selectedStrategies, setSelectedStrategies] = useState<string[]>([]);

  // 백테스팅 결과
  const [backtestResult, setBacktestResult] = useState<BacktestResult | null>(null);
  const [cumulativeResult, setCumulativeResult] = useState<BacktestCumulativeResult | null>(null);
  const [btLoading, setBtLoading] = useState(false);
  const [btError, setBtError] = useState('');

  // 시뮬레이션 결과
  const [simStrategy, setSimStrategy] = useState('');
  const [simResult, setSimResult] = useState<BacktestSimulateResult | null>(null);
  const [simLoading, setSimLoading] = useState(false);
  const [simError, setSimError] = useState('');

  useEffect(() => {
    fetchBacktestStrategies().then(r => {
      setStrategies(r.strategies);
      setSelectedStrategies(r.strategies.map(s => s.name));
    });
  }, []);

  const toggleStrategy = (name: string) => {
    setSelectedStrategies(prev =>
      prev.includes(name) ? prev.filter(s => s !== name) : [...prev, name]
    );
  };

  const handleRunBacktest = async () => {
    if (selectedStrategies.length === 0) return;
    setBtLoading(true);
    setBtError('');
    setBacktestResult(null);
    setCumulativeResult(null);
    setSimResult(null);
    try {
      const [bt, cum] = await Promise.all([
        runBacktest({ window: window_, games_per_pick: games, strategies: selectedStrategies }),
        runBacktestCumulative({ window: window_, games_per_pick: games, strategies: selectedStrategies, sample_every: 10 }),
      ]);
      setBacktestResult(bt);
      setCumulativeResult(cum);
      // 1위 기법 자동 선택
      if (bt.ranking.length > 0) setSimStrategy(bt.ranking[0]);
    } catch {
      setBtError('백테스팅 실행 실패. 데이터를 먼저 수집하세요.');
    } finally {
      setBtLoading(false);
    }
  };

  const handleRunSimulate = async () => {
    if (!simStrategy) return;
    setSimLoading(true);
    setSimError('');
    setSimResult(null);
    try {
      const r = await runBacktestSimulate({ strategy: simStrategy, window: window_, games_per_pick: games });
      setSimResult(r);
    } catch {
      setSimError('시뮬레이션 실패');
    } finally {
      setSimLoading(false);
    }
  };

  // 누적 차트 데이터
  const chartData = cumulativeResult
    ? cumulativeResult.rounds.map((round, i) => {
        const point: Record<string, number> = { round };
        for (const name of Object.keys(cumulativeResult.series)) {
          point[name] = cumulativeResult.series[name][i] ?? 0;
        }
        return point;
      })
    : [];

  // 기법 비교 바 차트 데이터
  const rankingData = backtestResult
    ? backtestResult.ranking.map(name => ({
        name: backtestResult.strategies[name].label,
        key: name,
        score: backtestResult.strategies[name].score,
        hit: backtestResult.strategies[name].hit_count,
        roi: backtestResult.strategies[name].roi,
      }))
    : [];

  return (
    <div className="backtest-page">
      <h1 className="page-title">백테스팅 &amp; 기법 시뮬레이션</h1>
      <p className="page-desc">
        역대 회차 데이터로 번호 예측 기법들을 검증하고, 가장 성과가 좋은 기법으로 전체 시뮬레이션을 실행합니다.
      </p>

      {/* ── STEP 1: 설정 ── */}
      <section className="section bt-config-section">
        <h2 className="section-title">STEP 1 — 백테스팅 설정</h2>
        <div className="config-row">
          <label>
            학습 윈도우 (회차)
            <input type="number" min={10} max={500} value={window_}
              onChange={e => setWindow(Number(e.target.value))} />
          </label>
          <label>
            회차당 예측 게임
            <input type="number" min={1} max={20} value={games}
              onChange={e => setGames(Number(e.target.value))} />
          </label>
        </div>

        <div className="strategy-toggle-row">
          {strategies.map(s => (
            <button
              key={s.name}
              className={`strategy-chip ${selectedStrategies.includes(s.name) ? 'active' : ''}`}
              onClick={() => toggleStrategy(s.name)}
            >
              {s.label}
            </button>
          ))}
        </div>

        <button
          className="btn-primary bt-run-btn"
          onClick={handleRunBacktest}
          disabled={btLoading || selectedStrategies.length === 0}
        >
          {btLoading ? '백테스팅 실행 중... (수초 소요)' : '백테스팅 실행'}
        </button>
        {btError && <div className="error-msg">{btError}</div>}
      </section>

      {/* ── STEP 2: 백테스팅 결과 ── */}
      {backtestResult && (
        <>
          <section className="section">
            <h2 className="section-title">
              STEP 2 — 백테스팅 결과
              <span className="section-sub">
                {backtestResult.total_rounds}회차 검증 · 윈도우 {backtestResult.window}회 · 회차당 {backtestResult.games_per_pick}게임
              </span>
            </h2>

            {/* 기법 랭킹 테이블 */}
            <div className="ranking-table-wrap">
              <table className="ranking-table">
                <thead>
                  <tr>
                    <th>순위</th>
                    <th>기법</th>
                    <th>스코어</th>
                    <th>적중 횟수</th>
                    <th>5등</th>
                    <th>4등</th>
                    <th>3등</th>
                    <th>2등</th>
                    <th>1등</th>
                    <th>ROI</th>
                  </tr>
                </thead>
                <tbody>
                  {backtestResult.ranking.map((name, idx) => {
                    const s = backtestResult.strategies[name];
                    return (
                      <tr
                        key={name}
                        className={`ranking-row ${simStrategy === name ? 'selected' : ''}`}
                        onClick={() => setSimStrategy(name)}
                        title="클릭하여 시뮬레이션 기법으로 선택"
                      >
                        <td className="rank-badge-cell">
                          <span className={`rank-badge rank-${idx + 1}`}>{idx + 1}</span>
                        </td>
                        <td className="strategy-name-cell">
                          {s.label}
                          {simStrategy === name && <span className="selected-tag">선택됨</span>}
                        </td>
                        <td className="score-cell">{s.score.toLocaleString()}</td>
                        <td>{s.hit_count}</td>
                        <td>{s.rank_counts['5'] ?? 0}</td>
                        <td>{s.rank_counts['4'] ?? 0}</td>
                        <td>{s.rank_counts['3'] ?? 0}</td>
                        <td>{s.rank_counts['2'] ?? 0}</td>
                        <td className={s.rank_counts['1'] > 0 ? 'hit-1st' : ''}>
                          {s.rank_counts['1'] ?? 0}
                        </td>
                        <td className={s.roi >= 0 ? 'positive' : 'negative'}>{s.roi}%</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <p className="table-hint">행을 클릭하면 해당 기법으로 시뮬레이션 기법이 선택됩니다.</p>
            </div>

            {/* 스코어 바 차트 */}
            <h3 className="chart-subtitle">기법별 스코어 비교</h3>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={rankingData} layout="vertical" margin={{ left: 20 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tick={{ fontSize: 11 }} />
                <YAxis type="category" dataKey="name" tick={{ fontSize: 12 }} width={75} />
                <Tooltip formatter={(v: number) => [v.toLocaleString(), '스코어']} />
                <Bar dataKey="score" name="스코어" radius={[0, 4, 4, 0]}>
                  {rankingData.map((entry, idx) => (
                    <Cell
                      key={entry.key}
                      fill={entry.key === simStrategy ? '#e74c3c' : LINE_COLORS[idx % LINE_COLORS.length]}
                    />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </section>

          {/* 누적 성과 라인 차트 */}
          {cumulativeResult && chartData.length > 0 && (
            <section className="section">
              <h2 className="section-title">기법별 누적 스코어 추이</h2>
              <p className="section-desc">
                회차가 진행되면서 각 기법의 누적 점수가 어떻게 쌓이는지 확인합니다.
                기울기가 가파를수록 꾸준히 좋은 성과를 내는 기법입니다.
              </p>
              <ResponsiveContainer width="100%" height={320}>
                <LineChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="round" tick={{ fontSize: 11 }} label={{ value: '회차', position: 'insideBottomRight', offset: -4 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Legend />
                  {Object.keys(cumulativeResult.series).map((name, idx) => (
                    <Line
                      key={name}
                      type="monotone"
                      dataKey={name}
                      name={cumulativeResult.labels[name]}
                      stroke={LINE_COLORS[idx % LINE_COLORS.length]}
                      dot={false}
                      strokeWidth={name === simStrategy ? 3 : 1.5}
                      strokeDasharray={name === simStrategy ? undefined : ''}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </section>
          )}

          {/* ── STEP 3: 시뮬레이션 실행 ── */}
          <section className="section bt-sim-section">
            <h2 className="section-title">STEP 3 — 기법 선택 후 시뮬레이션</h2>
            <p className="section-desc">
              백테스팅 결과에서 기법을 선택(테이블 행 클릭)하고 전체 회차 시뮬레이션을 실행합니다.
            </p>

            <div className="sim-strategy-selector">
              {backtestResult.ranking.map(name => (
                <button
                  key={name}
                  className={`strategy-chip ${simStrategy === name ? 'active' : ''}`}
                  onClick={() => setSimStrategy(name)}
                >
                  {backtestResult.strategies[name].label}
                </button>
              ))}
            </div>

            <button
              className="btn-primary"
              onClick={handleRunSimulate}
              disabled={simLoading || !simStrategy}
            >
              {simLoading
                ? '시뮬레이션 실행 중...'
                : simStrategy
                  ? `"${backtestResult.strategies[simStrategy]?.label}" 시뮬레이션 실행`
                  : '기법을 선택하세요'}
            </button>
            {simError && <div className="error-msg">{simError}</div>}
          </section>
        </>
      )}

      {/* ── 시뮬레이션 결과 ── */}
      {simResult && (
        <section className="section">
          <h2 className="section-title">
            시뮬레이션 결과 — {simResult.label}
            <span className="section-sub">
              {simResult.total_rounds}회차 · 윈도우 {simResult.window}회 · 회차당 {simResult.games_per_pick}게임
            </span>
          </h2>

          {/* 요약 카드 */}
          <div className="stat-cards">
            <div className="stat-card">
              <div className="stat-label">총 지출</div>
              <div className="stat-value">{formatWon(simResult.total_spent)}원</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">총 당첨금</div>
              <div className="stat-value">{formatWon(simResult.total_prize)}원</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">순손익</div>
              <div className={`stat-value ${simResult.net >= 0 ? 'positive' : 'negative'}`}>
                {formatWon(simResult.net)}원
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">ROI</div>
              <div className={`stat-value ${simResult.roi >= 0 ? 'positive' : 'negative'}`}>
                {simResult.roi}%
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">총 적중 횟수</div>
              <div className="stat-value">{simResult.hit_count}회</div>
            </div>
            <div className="stat-card">
              <div className="stat-label">스코어</div>
              <div className="stat-value">{simResult.score.toLocaleString()}</div>
            </div>
          </div>

          {/* 등수별 분포 */}
          <h3 className="chart-subtitle">등수별 적중 횟수</h3>
          <div className="rank-summary">
            {[1, 2, 3, 4, 5].map(rank => (
              <div key={rank} className="rank-item" style={{ borderTop: `3px solid ${RANK_COLORS[rank]}` }}>
                <span className="rank-label">{rank}등</span>
                <span className="rank-count">{simResult.rank_counts[String(rank)] ?? 0}회</span>
              </div>
            ))}
            <div className="rank-item" style={{ borderTop: '3px solid #bbb' }}>
              <span className="rank-label">미당첨</span>
              <span className="rank-count">{simResult.rank_counts['0'] ?? 0}회</span>
            </div>
          </div>

          {/* 적중 회차 목록 */}
          {simResult.hit_rounds.length > 0 && (
            <>
              <h3 className="chart-subtitle">적중 회차 (최근 50개)</h3>
              <div className="hit-rounds-list">
                {simResult.hit_rounds.slice().reverse().map((hr, i) => (
                  <div key={i} className={`hit-round-item rank-${hr.rank}`}>
                    <div className="hit-round-meta">
                      <span className="hit-round-no">{hr.round}회</span>
                      <span className="hit-round-date">{hr.draw_date}</span>
                      <span className="hit-rank-badge" style={{ background: RANK_COLORS[hr.rank] }}>
                        {hr.rank}등
                      </span>
                    </div>
                    <div className="hit-round-balls">
                      {hr.actual.map(n => (
                        <LottoBall key={n} number={n} size="sm" />
                      ))}
                      <span className="bonus-sep">+</span>
                      <LottoBall number={hr.bonus} bonus size="sm" />
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </section>
      )}
    </div>
  );
}
