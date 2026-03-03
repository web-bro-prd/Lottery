import { useState, useEffect } from 'react';
import {
  fetchBacktestMethods,
  runBacktest,
  runBacktestCumulative,
  runBacktestRecommend,
  fetchFixedNumber,
} from '../api/lottery';
import type {
  BacktestMethodsResponse,
  BacktestResult,
  BacktestCumulativeResult,
  BacktestRecommendResult,
  FixedNumberResult,
} from '../types';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, BarChart, Bar, Cell,
} from 'recharts';
import LottoBall from '../components/LottoBall';
import './BacktestPage.css';

const METHOD_COLORS: Record<string, string> = {
  FREQUENCY:       '#3498db',
  WEIGHTED_RECENT: '#e74c3c',
  CYCLE:           '#2ecc71',
  TREND:           '#f39c12',
  ENSEMBLE:        '#9b59b6',
};

const METHOD_DESC: Record<string, string> = {
  FREQUENCY:       '과거 전체 최빈 조건',
  WEIGHTED_RECENT: '최근 20%에 3배 가중치 ★',
  CYCLE:           '최근 10회 모드',
  TREND:           '최근 상승 추세 조건',
  ENSEMBLE:        '4가지 다수결',
};

export default function BacktestPage() {
  const [meta, setMeta] = useState<BacktestMethodsResponse | null>(null);

  // 설정
  const [window_, setWindow] = useState(600);
  const [selectedMethods, setSelectedMethods] = useState<string[]>([]);
  const [simMethod, setSimMethod] = useState('WEIGHTED_RECENT');
  const [nGames, setNGames] = useState(20);

  // 결과
  const [btResult, setBtResult] = useState<BacktestResult | null>(null);
  const [cumResult, setCumResult] = useState<BacktestCumulativeResult | null>(null);
  const [recResult, setRecResult] = useState<BacktestRecommendResult | null>(null);

  const [fixedResult, setFixedResult] = useState<FixedNumberResult | null>(null);
  const [fixedLoading, setFixedLoading] = useState(false);
  const [fixedError, setFixedError] = useState('');

  const [btLoading, setBtLoading] = useState(false);
  const [recLoading, setRecLoading] = useState(false);
  const [btError, setBtError] = useState('');
  const [recError, setRecError] = useState('');

  useEffect(() => {
    fetchBacktestMethods().then(r => {
      setMeta(r);
      setSelectedMethods(r.methods);
    });
  }, []);

  const toggleMethod = (m: string) =>
    setSelectedMethods(prev =>
      prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m]
    );

  const handleRunBacktest = async () => {
    if (selectedMethods.length === 0) return;
    setBtLoading(true);
    setBtError('');
    setBtResult(null);
    setCumResult(null);
    setRecResult(null);
    try {
      const [bt, cum] = await Promise.all([
        runBacktest({ window: window_, methods: selectedMethods }),
        runBacktestCumulative({ window: window_, methods: selectedMethods, sample_every: 10 }),
      ]);
      setBtResult(bt);
      setCumResult(cum);
      setSimMethod(bt.best_method);
    } catch {
      setBtError('백테스팅 실패. 데이터를 먼저 수집하세요.');
    } finally {
      setBtLoading(false);
    }
  };

  const handleRecommend = async () => {
    setRecLoading(true);
    setRecError('');
    setRecResult(null);
    try {
      const r = await runBacktestRecommend({ method: simMethod, window: window_, n_games: nGames });
      setRecResult(r);
    } catch {
      setRecError('번호 추천 실패');
    } finally {
      setRecLoading(false);
    }
  };

  const handleFixedNumber = async () => {
    setFixedLoading(true);
    setFixedError('');
    setFixedResult(null);
    try {
      const r = await fetchFixedNumber();
      setFixedResult(r);
    } catch {
      setFixedError('고정번호 발급 실패. 데이터를 먼저 수집하세요.');
    } finally {
      setFixedLoading(false);
    }
  };

  // 조건별 정확도 차트 데이터
  const condAccData = btResult
    ? Object.entries(btResult.condition_accuracy_avg)
        .map(([key, acc]) => ({
          key,
          label: btResult.condition_labels[key] ?? key,
          avg: acc,
          best: btResult.methods[btResult.best_method]?.condition_accuracy[key] ?? 0,
        }))
        .sort((a, b) => b.best - a.best)
    : [];

  // 누적 정확도 차트 데이터
  const cumChartData = cumResult
    ? cumResult.rounds.map((round, i) => {
        const pt: Record<string, number> = { round };
        for (const m of Object.keys(cumResult.series)) {
          pt[m] = cumResult.series[m][i] ?? 0;
        }
        return pt;
      })
    : [];

  return (
    <div className="backtest-page">
      <h1 className="page-title">백테스팅 &amp; 번호 추천</h1>
      <p className="page-desc">
        13개 조건 × 5가지 예측 방법으로 역대 회차를 검증하고, 가장 정확한 방법으로 다음 회차 번호를 추천합니다.
      </p>

      {/* ── STEP 1: 설정 ── */}
      <section className="section bt-config-section">
        <h2 className="section-title">STEP 1 — 백테스팅 설정</h2>
        <p className="section-desc">
          학습 윈도우: 처음 N회차 데이터로 조건 패턴을 학습하고, 이후 회차에서 예측합니다.
          기존 분석 보고서 기준은 600회입니다.
        </p>
        <div className="config-row">
          <label>
            학습 윈도우 (회차)
            <input type="number" min={50} max={1200} value={window_}
              onChange={e => setWindow(Number(e.target.value))} />
          </label>
        </div>

        <div className="strategy-toggle-row">
          {(meta?.methods ?? []).map(m => (
            <button
              key={m}
              className={`strategy-chip ${selectedMethods.includes(m) ? 'active' : ''}`}
              style={selectedMethods.includes(m) ? { background: METHOD_COLORS[m], borderColor: METHOD_COLORS[m] } : {}}
              onClick={() => toggleMethod(m)}
              title={METHOD_DESC[m]}
            >
              {m}
            </button>
          ))}
        </div>

        <button
          className="btn-primary bt-run-btn"
          onClick={handleRunBacktest}
          disabled={btLoading || selectedMethods.length === 0}
        >
          {btLoading ? '백테스팅 실행 중... (수십 초 소요)' : '백테스팅 실행'}
        </button>
        {btError && <div className="error-msg">{btError}</div>}
      </section>

      {/* ── STEP 2: 백테스팅 결과 ── */}
      {btResult && (
        <>
          <section className="section">
            <h2 className="section-title">
              STEP 2 — 백테스팅 결과
              <span className="section-sub">
                {btResult.total_tested}회차 검증 · 윈도우 {btResult.window}회
              </span>
            </h2>

            {/* 예측 방법 랭킹 */}
            <h3 className="chart-subtitle">예측 방법별 평균 정확도</h3>
            <div className="method-ranking">
              {btResult.ranking.map(([method, acc], idx) => (
                <div
                  key={method}
                  className={`method-card ${simMethod === method ? 'selected' : ''}`}
                  onClick={() => setSimMethod(method)}
                  style={{ borderTop: `4px solid ${METHOD_COLORS[method] ?? '#aaa'}` }}
                >
                  <div className="method-rank">#{idx + 1}</div>
                  <div className="method-name">{method}</div>
                  <div className="method-desc">{METHOD_DESC[method] ?? ''}</div>
                  <div className="method-acc" style={{ color: METHOD_COLORS[method] }}>
                    {acc.toFixed(2)}%
                  </div>
                  {simMethod === method && <div className="selected-tag">선택됨</div>}
                </div>
              ))}
            </div>
            <p className="table-hint">카드를 클릭하면 STEP 3 번호 추천에 사용할 방법이 선택됩니다.</p>

            {/* 조건별 정확도 바 차트 */}
            <h3 className="chart-subtitle">
              조건별 정확도 — {btResult.best_method}(★최고) vs 전체 평균
            </h3>
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={condAccData} layout="vertical" margin={{ left: 10, right: 30 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" unit="%" tick={{ fontSize: 11 }} domain={[0, 60]} />
                <YAxis type="category" dataKey="label" tick={{ fontSize: 12 }} width={90} />
                <Tooltip formatter={(v: number) => [`${v.toFixed(1)}%`]} />
                <Legend />
                <Bar dataKey="best" name={`${btResult.best_method}`} fill={METHOD_COLORS[btResult.best_method] ?? '#e74c3c'} radius={[0, 4, 4, 0]} />
                <Bar dataKey="avg" name="전체 평균" fill="#bdc3c7" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </section>

          {/* 누적 정확도 추이 */}
          {cumResult && cumChartData.length > 0 && (
            <section className="section">
              <h2 className="section-title">예측 방법별 누적 정확도 추이</h2>
              <p className="section-desc">
                회차가 쌓일수록 각 방법의 평균 정확도가 어떻게 변화하는지 보여줍니다.
                안정적으로 수렴하는 방법이 신뢰도가 높습니다.
              </p>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={cumChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="round" tick={{ fontSize: 11 }} label={{ value: '회차', position: 'insideBottomRight', offset: -4 }} />
                  <YAxis tick={{ fontSize: 11 }} unit="%" />
                  <Tooltip formatter={(v: number) => [`${v.toFixed(2)}%`]} />
                  <Legend />
                  {Object.keys(cumResult.series).map(m => (
                    <Line
                      key={m}
                      type="monotone"
                      dataKey={m}
                      name={m}
                      stroke={METHOD_COLORS[m] ?? '#888'}
                      dot={false}
                      strokeWidth={m === simMethod ? 3 : 1.5}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </section>
          )}

          {/* ── STEP 3: 번호 추천 ── */}
          <section className="section bt-sim-section">
            <h2 className="section-title">STEP 3 — 예측 조건 기반 번호 추천</h2>
            <p className="section-desc">
              선택한 방법으로 다음 회차의 조건(홀짝 비율, 연속번호 등)을 예측한 뒤,
              해당 조건을 가장 잘 만족하는 번호 조합을 생성합니다.
            </p>

            <div className="sim-strategy-selector">
              {btResult.ranking.map(([m]) => (
                <button
                  key={m}
                  className={`strategy-chip ${simMethod === m ? 'active' : ''}`}
                  style={simMethod === m ? { background: METHOD_COLORS[m], borderColor: METHOD_COLORS[m] } : {}}
                  onClick={() => setSimMethod(m)}
                >
                  {m}
                </button>
              ))}
            </div>

            <div className="config-row" style={{ marginTop: 12 }}>
              <label>
                추천 게임 수
                <input type="number" min={5} max={50} value={nGames}
                  onChange={e => setNGames(Number(e.target.value))} />
              </label>
              <button className="btn-primary" onClick={handleRecommend} disabled={recLoading}>
                {recLoading ? '번호 생성 중...' : `"${simMethod}" 방법으로 ${nGames}게임 추천`}
              </button>
            </div>
            {recError && <div className="error-msg">{recError}</div>}
          </section>
        </>
      )}

      {/* ── STEP 4: 고정번호 발급 ── */}
      <section className="section fixed-section">
        <h2 className="section-title">STEP 4 — 매주 고정 구매 번호 발급</h2>
        <p className="section-desc">
          역대 <strong>전체 회차의 조건 최빈값</strong>을 산출하여, 가장 자주 등장한 구조를 가진 번호 1조를 발급합니다.
          꾸준히 같은 번호를 구매할 때 장기적으로 커버 확률이 최대화되는 조합입니다.
        </p>
        <div className="fixed-strategy-box">
          <div className="fixed-strategy-item">✅ 홀짝 비율 — 역대 최빈 패턴</div>
          <div className="fixed-strategy-item">✅ 고저 분포 — 역대 최빈 패턴</div>
          <div className="fixed-strategy-item">✅ 합계 — 역대 중앙값 ±25 범위</div>
          <div className="fixed-strategy-item">✅ AC값 4 이상 — 번호 간격 다양성 확보</div>
          <div className="fixed-strategy-item">✅ 끝자리 중복 최소화</div>
          <div className="fixed-strategy-item">✅ 연속번호 최대 1쌍</div>
        </div>
        <button
          className="btn-fixed"
          onClick={handleFixedNumber}
          disabled={fixedLoading}
        >
          {fixedLoading ? '번호 산출 중...' : '고정번호 발급받기'}
        </button>
        {fixedError && <div className="error-msg">{fixedError}</div>}

        {fixedResult && (
          <div className="fixed-result">
            <div className="fixed-balls-row">
              {fixedResult.numbers.map(n => (
                <LottoBall key={n} number={n} size="lg" />
              ))}
            </div>
            <div className="fixed-score">
              조건 부합도 {(fixedResult.score * 100).toFixed(0)}%
            </div>

            <h3 className="chart-subtitle">선택 근거</h3>
            <div className="fixed-rationale">
              {Object.entries(fixedResult.rationale).map(([key, desc]) => (
                <div key={key} className="rationale-item">
                  <span className="rationale-icon">📌</span>
                  <span>{desc}</span>
                </div>
              ))}
            </div>

            <h3 className="chart-subtitle">이 번호의 조건 상세</h3>
            <div className="predicted-conds">
              {Object.entries(fixedResult.all_conditions)
                .filter(([k]) => fixedResult.condition_labels[k])
                .map(([key, val]) => {
                  const target = fixedResult.target_conditions[key];
                  const matched = val === target;
                  return (
                    <div key={key} className={`pred-cond-item ${matched ? 'matched' : 'unmatched'}`}>
                      <span className="pred-cond-label">
                        {fixedResult.condition_labels[key]}
                      </span>
                      <span className="pred-cond-value">
                        {val}
                        {matched
                          ? <span className="match-tag">✓ 최빈값</span>
                          : <span className="unmatch-tag">최빈: {target}</span>
                        }
                      </span>
                    </div>
                  );
                })}
            </div>
          </div>
        )}
      </section>

      {/* ── 추천 번호 결과 ── */}
      {recResult && (
        <section className="section">
          <h2 className="section-title">
            추천 번호 — {recResult.method}
            <span className="section-sub">윈도우 {recResult.window}회 · {recResult.n_games}게임</span>
          </h2>

          {/* 예측된 조건 */}
          <h3 className="chart-subtitle">예측된 다음 회차 조건</h3>
          <div className="predicted-conds">
            {Object.entries(recResult.predicted_conditions).map(([key, val]) => (
              <div key={key} className="pred-cond-item">
                <span className="pred-cond-label">
                  {recResult.condition_labels[key] ?? key}
                </span>
                <span className="pred-cond-value">{val}</span>
              </div>
            ))}
          </div>

          {/* 추천 번호 목록 */}
          <h3 className="chart-subtitle">추천 번호 (조건 부합도 순)</h3>
          <div className="rec-games-list">
            {recResult.games.map((game, i) => (
              <div key={i} className="rec-game-row">
                <span className="rec-game-no">{i + 1}</span>
                <div className="rec-game-balls">
                  {game.map(n => (
                    <LottoBall key={n} number={n} size="md" />
                  ))}
                </div>
                <span className="rec-game-score">
                  적합도 {(recResult.scores[i] * 100).toFixed(0)}%
                </span>
              </div>
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
