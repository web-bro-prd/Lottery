import { useState, useEffect, useCallback } from 'react';
import {
  fetchStatus,
  fetchBacktestMethods,
  runBacktest,
  runBacktestCumulative,
  runBacktestRecommend,
  fetchFixedNumber,
  getFixedNumbers,
  saveFixedNumber,
  deleteFixedNumber,
  updateFixedMemo,
  runRealSim,
  runPatternRecommend,
  startPatternSim,
  pollPatternSim,
  runWeeklyPick,
} from '../api/lottery';
import type {
  BacktestMethodsResponse,
  BacktestResult,
  BacktestCumulativeResult,
  BacktestRecommendResult,
  FixedNumberResult,
  SavedFixedNumber,
  RealSimResult,
  PatternRecommendResult,
  PatternSimResult,
  WeeklyPickResult,
} from '../types';
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  Legend, ResponsiveContainer, BarChart, Bar,
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
  const [totalRounds, setTotalRounds] = useState<number>(0);

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
  const [fixedSaving, setFixedSaving] = useState(false);
  const [fixedSaveMsg, setFixedSaveMsg] = useState('');

  // 저장된 고정번호 목록
  const [savedList, setSavedList] = useState<SavedFixedNumber[]>([]);
  const [savedLoading, setSavedLoading] = useState(false);
  const [editingMemoId, setEditingMemoId] = useState<number | null>(null);
  const [editingMemoText, setEditingMemoText] = useState('');

  // 실전 시뮬레이션
  const [realSimResult, setRealSimResult] = useState<RealSimResult | null>(null);
  const [realSimLoading, setRealSimLoading] = useState(false);
  const [realSimError, setRealSimError] = useState('');
  const [realSimMethod, setRealSimMethod] = useState('WEIGHTED_RECENT');
  const [realSimGames, setRealSimGames] = useState(9);
  const [realSimSampleEvery, setRealSimSampleEvery] = useState(10);
  const [showDetail, setShowDetail] = useState(false);

  // 패턴 기반 추천
  const [patternRecResult, setPatternRecResult] = useState<PatternRecommendResult | null>(null);
  const [patternRecLoading, setPatternRecLoading] = useState(false);
  const [patternRecError, setPatternRecError] = useState('');
  const [patternNGames, setPatternNGames] = useState(9);

  // 이번 주 추천 10게임
  const [weeklyResult, setWeeklyResult] = useState<WeeklyPickResult | null>(null);
  const [weeklyLoading, setWeeklyLoading] = useState(false);
  const [weeklyError, setWeeklyError] = useState('');

  // STEP3 탭
  const [step3Tab, setStep3Tab] = useState<'condition' | 'pattern'>('condition');

  // STEP5 탭 + 통합 시뮬레이션
  const [step5Tab, setStep5Tab] = useState<'condition' | 'integrated'>('condition');
  const [patternSimResult, setPatternSimResult] = useState<PatternSimResult | null>(null);
  const [patternSimLoading, setPatternSimLoading] = useState(false);
  const [patternSimError, setPatternSimError] = useState('');
  const [simNGames, setSimNGames] = useState(9);
  const [simSampleEvery, setSimSampleEvery] = useState(5);
  const [simCondWindow, setSimCondWindow] = useState(300);
  const [showSimDetail, setShowSimDetail] = useState(false);

  const [btLoading, setBtLoading] = useState(false);
  const [recLoading, setRecLoading] = useState(false);
  const [btError, setBtError] = useState('');
  const [recError, setRecError] = useState('');

  const loadSavedList = useCallback(() => {
    setSavedLoading(true);
    getFixedNumbers()
      .then(setSavedList)
      .finally(() => setSavedLoading(false));
  }, []);

  useEffect(() => {
    fetchBacktestMethods().then(r => {
      setMeta(r);
      setSelectedMethods(r.methods);
    });
    fetchStatus().then(r => {
      if (r.total_rounds) setTotalRounds(r.total_rounds);
    });
    loadSavedList();
  }, [loadSavedList]);

  const toggleMethod = (m: string) =>
    setSelectedMethods(prev =>
      prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m]
    );

  const handleRunBacktest = async () => {
    if (selectedMethods.length === 0) return;
    // 윈도우 유효성 검사 (서버 조건: window + 5 <= totalRounds)
    const maxWindow = totalRounds > 5 ? totalRounds - 5 : totalRounds;
    if (window_ > maxWindow) {
      setBtError(`학습 윈도우(${window_})가 너무 큽니다. 전체 데이터(${totalRounds}회) 기준 최대 ${maxWindow}까지 가능합니다.`);
      return;
    }
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
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setBtError(detail ? `백테스팅 실패: ${detail}` : '백테스팅 실패. 데이터를 먼저 수집하세요.');
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
    setFixedSaveMsg('');
    try {
      const r = await fetchFixedNumber();
      setFixedResult(r);
    } catch {
      setFixedError('고정번호 발급 실패. 데이터를 먼저 수집하세요.');
    } finally {
      setFixedLoading(false);
    }
  };

  const handleSaveFixed = async () => {
    if (!fixedResult) return;
    setFixedSaving(true);
    setFixedSaveMsg('');
    try {
      await saveFixedNumber({
        numbers: fixedResult.numbers,
        score: fixedResult.score,
        rationale: fixedResult.rationale,
      });
      setFixedSaveMsg('저장 완료!');
      loadSavedList();
    } catch {
      setFixedSaveMsg('저장 실패');
    } finally {
      setFixedSaving(false);
    }
  };

  const handleDeleteFixed = async (id: number) => {
    if (!window.confirm('이 고정번호를 삭제하시겠습니까?')) return;
    await deleteFixedNumber(id);
    loadSavedList();
  };

  const handleMemoSave = async (id: number) => {
    await updateFixedMemo(id, editingMemoText);
    setEditingMemoId(null);
    loadSavedList();
  };

  const handlePatternSim = async () => {
    setPatternSimLoading(true);
    setPatternSimError('');
    setPatternSimResult(null);
    setShowSimDetail(false);
    try {
      // 1. 작업 시작 → task_id 수신
      const { task_id } = await startPatternSim({
        n_games: simNGames,
        sample_every: simSampleEvery,
        condition_window: simCondWindow,
      });

      // 2. 3초마다 폴링
      await new Promise<void>((resolve, reject) => {
        const interval = setInterval(async () => {
          try {
            const res = await pollPatternSim(task_id);
            if (res.status === 'done') {
              clearInterval(interval);
              setPatternSimResult(res as PatternSimResult);
              resolve();
            } else if (res.status === 'error') {
              clearInterval(interval);
              reject(new Error('서버 처리 오류'));
            }
            // status === 'running' 이면 계속 대기
          } catch (pollErr) {
            clearInterval(interval);
            reject(pollErr);
          }
        }, 3000);
      });
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setPatternSimError(detail ?? (e instanceof Error ? e.message : '시뮬레이션 실패'));
    } finally {
      setPatternSimLoading(false);
    }
  };

  const handlePatternRecommend = async () => {
    setPatternRecLoading(true);
    setPatternRecError('');
    setPatternRecResult(null);
    try {
      const r = await runPatternRecommend(patternNGames);
      setPatternRecResult(r);
    } catch {
      setPatternRecError('패턴 기반 번호 추천 실패. 데이터를 먼저 수집하세요.');
    } finally {
      setPatternRecLoading(false);
    }
  };

  const handleWeeklyPick = async () => {
    setWeeklyLoading(true);
    setWeeklyError('');
    setWeeklyResult(null);
    try {
      const r = await runWeeklyPick();
      setWeeklyResult(r);
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setWeeklyError(detail ?? '이번 주 추천 생성 실패');
    } finally {
      setWeeklyLoading(false);
    }
  };

  const handleRealSim = async () => {
    setRealSimLoading(true);
    setRealSimError('');
    setRealSimResult(null);
    setShowDetail(false);
    try {
      const r = await runRealSim({
        method: realSimMethod,
        window: window_,
        n_games: realSimGames,
        sample_every: realSimSampleEvery,
      });
      setRealSimResult(r);
    } catch {
      setRealSimError('실전 시뮬레이션 실패. 데이터를 먼저 수집하세요.');
    } finally {
      setRealSimLoading(false);
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
            <input
              type="number"
              min={50}
              max={totalRounds > 5 ? totalRounds - 5 : 1200}
              value={window_}
              onChange={e => setWindow(Number(e.target.value))}
            />
          </label>
          {totalRounds > 0 && (
            <span className="window-hint">
              전체 {totalRounds}회차 · 최대 {totalRounds - 5}회 설정 가능
            </span>
          )}
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

        </>
      )}

      {/* ── STEP 3: 번호 추천 (탭) — btResult 독립, 항상 표시 ── */}
      <section className="section bt-sim-section">
        <h2 className="section-title">STEP 3 — 번호 추천</h2>

        {/* 탭 헤더 */}
        <div className="step3-tabs">
          <button
            className={`step3-tab ${step3Tab === 'condition' ? 'active' : ''}`}
            onClick={() => setStep3Tab('condition')}
          >
            예측 조건 기반
          </button>
          <button
            className={`step3-tab pattern-tab ${step3Tab === 'pattern' ? 'active' : ''}`}
            onClick={() => setStep3Tab('pattern')}
          >
            패턴 기반 ★
          </button>
        </div>

        {/* 탭 1: 예측 조건 기반 (백테스팅 결과 필요) */}
        {step3Tab === 'condition' && (
          <div className="step3-tab-content">
            <p className="section-desc">
              선택한 방법으로 다음 회차의 조건(홀짝 비율, 연속번호 등)을 예측한 뒤,
              해당 조건을 가장 잘 만족하는 번호 조합을 생성합니다.
              먼저 <strong>STEP 1 백테스팅을 실행</strong>해야 사용 가능합니다.
            </p>
            {!btResult ? (
              <div className="signal-none">STEP 1 백테스팅을 먼저 실행하세요.</div>
            ) : (
              <>
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
              </>
            )}
          </div>
        )}

        {/* 탭 2: 패턴 기반 (백테스팅 불필요, 독립 실행) */}
        {step3Tab === 'pattern' && (
          <div className="step3-tab-content">
            <p className="section-desc">
              통계적으로 유의한 신호(합계 방향 반전 p&lt;0.0001, 극단 합계 회귀 p=0.0123)를 감지해
              다음 회차 합계 타겟 범위를 좁히고 번호를 생성합니다.
              <strong> 백테스팅 없이 바로 사용 가능합니다.</strong>
            </p>
            <div className="config-row" style={{ marginTop: 12 }}>
              <label>
                추천 게임 수
                <input type="number" min={1} max={50} value={patternNGames}
                  onChange={e => setPatternNGames(Number(e.target.value))} />
              </label>
              <button
                className="btn-primary btn-pattern"
                onClick={handlePatternRecommend}
                disabled={patternRecLoading}
              >
                {patternRecLoading ? '신호 분석 중...' : `패턴 신호 감지 후 ${patternNGames}게임 추천`}
              </button>
            </div>
            {patternRecError && <div className="error-msg">{patternRecError}</div>}

            {patternRecResult && (
              <div className="pattern-rec-result">
                {/* 감지된 신호 */}
                <h3 className="chart-subtitle">감지된 패턴 신호</h3>
                {patternRecResult.detected_signals.length === 0 ? (
                  <div className="signal-none">
                    유의한 신호 없음 — 전체 평균 범위 적용
                  </div>
                ) : (
                  <div className="signal-list">
                    {patternRecResult.detected_signals.map((sig, i) => (
                      <div key={i} className={`signal-item strength-${sig.strength}`}>
                        <div className="signal-header">
                          <span className="signal-badge">신호 {sig.name}</span>
                          <span className={`signal-strength ${sig.strength}`}>
                            {sig.strength === 'high' ? '★★ 강함' : sig.strength === 'medium' ? '★ 중간' : '◎ 약함'}
                          </span>
                        </div>
                        <div className="signal-desc">{sig.desc}</div>
                        <div className="signal-stat">{sig.stat}</div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 합계 타겟 범위 */}
                <div className="pattern-target-box">
                  <div className="pattern-target-label">합계 타겟 범위</div>
                  <div className="pattern-target-range">
                    {patternRecResult.target_sum_min} ~ {patternRecResult.target_sum_max}
                  </div>
                  <div className="pattern-recent-sums">
                    최근 3회 합계: {patternRecResult.recent_sums.join(' → ')}
                  </div>
                </div>

                {/* 근거 */}
                <div className="pattern-rationale">
                  {patternRecResult.rationale}
                </div>

                {/* 추천 번호 */}
                <h3 className="chart-subtitle">추천 번호 (합계 타겟 범위 내, 조건 부합도 순)</h3>
                <div className="rec-games-list">
                  {patternRecResult.games.map((game, i) => (
                    <div key={i} className="rec-game-row">
                      <span className="rec-game-no">{i + 1}</span>
                      <div className="rec-game-balls">
                        {game.map(n => (
                          <LottoBall key={n} number={n} size="md" />
                        ))}
                      </div>
                      <span className="rec-game-score">
                        적합도 {(patternRecResult.scores[i] * 100).toFixed(0)}%
                      </span>
                      <span className="rec-game-sum">
                        합계 {game.reduce((a, b) => a + b, 0)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </section>

      {/* ── STEP 3.5: 이번 주 추천 10게임 ── */}
      <section className="section weekly-pick-section">
        <h2 className="section-title">
          STEP 3.5 — 이번 주 추천 10게임
          <span className="section-sub new-badge">NEW</span>
        </h2>
        <p className="section-desc">
          <strong>고정 1 + 조건 기반 4 + 패턴 기반 5</strong>게임을 한 번에 생성합니다.
          내부적으로 역대 당첨 유사 회차의 조건을 역추적해 인사이트도 함께 제공합니다.
          <br />
          <strong>주의:</strong> 경량 시뮬레이션이 포함되어 수십 초 소요됩니다.
        </p>
        <button
          className="btn-primary btn-weekly"
          onClick={handleWeeklyPick}
          disabled={weeklyLoading}
        >
          {weeklyLoading ? '분석 중... (수십 초 소요)' : '이번 주 추천 10게임 생성'}
        </button>
        {weeklyError && <div className="error-msg">{weeklyError}</div>}

        {weeklyResult && (() => {
          const { fixed, condition, pattern, winning_insight, all_games, source_labels } = weeklyResult;
          const SOURCE_COLORS: Record<string, string> = {
            '고정': '#9b59b6',
            '조건': '#3498db',
            '패턴': '#e74c3c',
          };
          return (
            <div className="weekly-result">
              {/* 전체 10게임 한눈에 보기 */}
              <h3 className="chart-subtitle">전체 추천 10게임</h3>
              <div className="weekly-all-games">
                {all_games.map((game, i) => {
                  const label = source_labels[i] ?? '';
                  const color = SOURCE_COLORS[label] ?? '#aaa';
                  const score = label === '고정'
                    ? fixed.score
                    : label === '조건'
                      ? condition.scores[i - 1]
                      : pattern.scores[i - 1 - condition.games.length];
                  return (
                    <div key={i} className="weekly-game-row">
                      <span className="weekly-game-badge" style={{ background: color }}>
                        {label}
                      </span>
                      <span className="weekly-game-no">{i + 1}</span>
                      <div className="rec-game-balls">
                        {game.map(n => <LottoBall key={n} number={n} size="md" />)}
                      </div>
                      <span className="rec-game-score">
                        적합도 {(score * 100).toFixed(0)}%
                      </span>
                      <span className="rec-game-sum">합계 {game.reduce((a, b) => a + b, 0)}</span>
                    </div>
                  );
                })}
              </div>

              {/* 섹션별 근거 */}
              <div className="weekly-breakdown">
                {/* 고정번호 근거 */}
                <div className="weekly-breakdown-card card-fixed">
                  <div className="weekly-breakdown-title" style={{ color: '#9b59b6' }}>
                    고정번호 — 역대 최빈 조건
                  </div>
                  <div className="weekly-breakdown-body">
                    {Object.values(fixed.rationale).map((desc, i) => (
                      <div key={i} className="rationale-item">
                        <span className="rationale-icon">📌</span>
                        <span>{desc}</span>
                      </div>
                    ))}
                  </div>
                </div>

                {/* 조건 기반 근거 */}
                <div className="weekly-breakdown-card card-condition">
                  <div className="weekly-breakdown-title" style={{ color: '#3498db' }}>
                    조건 기반 4게임 — WEIGHTED_RECENT 예측
                  </div>
                  <div className="weekly-breakdown-body">
                    <div className="weekly-signal-list">
                      {['odd_even', 'high_low', 'sum_range', 'consecutive', 'tail_dist'].map(key => {
                        const label = condition.condition_labels[key] ?? key;
                        const val = condition.predicted_conditions[key];
                        return val ? (
                          <span key={key} className="weekly-cond-chip">
                            {label}: <strong>{val}</strong>
                          </span>
                        ) : null;
                      })}
                    </div>
                  </div>
                </div>

                {/* 패턴 기반 근거 */}
                <div className="weekly-breakdown-card card-pattern">
                  <div className="weekly-breakdown-title" style={{ color: '#e74c3c' }}>
                    패턴 기반 5게임 — 합계 신호
                  </div>
                  <div className="weekly-breakdown-body">
                    <div className="pattern-target-box" style={{ marginBottom: 8 }}>
                      <div className="pattern-target-label">합계 타겟 범위</div>
                      <div className="pattern-target-range">
                        {pattern.target_sum_min} ~ {pattern.target_sum_max}
                      </div>
                      <div className="pattern-recent-sums">
                        최근 3회 합계: {pattern.recent_sums.join(' → ')}
                      </div>
                    </div>
                    {pattern.detected_signals.length > 0 ? (
                      <div className="signal-list">
                        {pattern.detected_signals.map((sig, i) => (
                          <div key={i} className={`signal-item strength-${sig.strength}`}>
                            <div className="signal-header">
                              <span className="signal-badge">신호 {sig.name}</span>
                              <span className={`signal-strength ${sig.strength}`}>
                                {sig.strength === 'high' ? '★★ 강함' : sig.strength === 'medium' ? '★ 중간' : '◎ 약함'}
                              </span>
                            </div>
                            <div className="signal-desc">{sig.desc}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="signal-none">유의한 신호 없음 — 평균 범위 적용</div>
                    )}
                  </div>
                </div>
              </div>

              {/* 당첨 역추적 인사이트 */}
              <div className="winning-insight-box">
                <h3 className="chart-subtitle">
                  당첨 역추적 인사이트
                  <span className="section-sub">{winning_insight.total_hit_rounds}건 분석</span>
                </h3>
                <p className="winning-insight-desc">{winning_insight.insight}</p>
                {winning_insight.top_conditions.length > 0 && (
                  <div className="winning-top-conds">
                    <div className="winning-top-conds-label">당첨 유사 회차의 공통 조건 TOP 5</div>
                    <div className="winning-cond-chips">
                      {winning_insight.top_conditions.map((tc, i) => (
                        <div key={i} className="winning-cond-item">
                          <span className="winning-cond-label">{tc.label}</span>
                          <span className="winning-cond-value">{tc.top_value}</span>
                          <span className="winning-cond-pct">{tc.pct}%</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          );
        })()}
      </section>

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

            <div className="fixed-save-row">
              <button
                className="btn-save-fixed"
                onClick={handleSaveFixed}
                disabled={fixedSaving}
              >
                {fixedSaving ? '저장 중...' : '이 번호 저장하기'}
              </button>
              {fixedSaveMsg && (
                <span className={`save-msg ${fixedSaveMsg.includes('실패') ? 'fail' : 'ok'}`}>
                  {fixedSaveMsg}
                </span>
              )}
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

        {/* ── 저장된 고정번호 목록 ── */}
        <div className="saved-fixed-section">
          <h3 className="chart-subtitle">
            저장된 고정번호 목록
            <span className="section-sub">{savedList.length}개 저장됨</span>
          </h3>
          {savedLoading && <p className="saved-loading">불러오는 중...</p>}
          {!savedLoading && savedList.length === 0 && (
            <p className="saved-empty">저장된 고정번호가 없습니다. 번호를 발급받고 저장해보세요.</p>
          )}
          <div className="saved-list">
            {savedList.map(item => (
              <div key={item.id} className="saved-item">
                <div className="saved-item-balls">
                  {item.numbers.map(n => (
                    <LottoBall key={n} number={n} size="sm" />
                  ))}
                  {item.score != null && (
                    <span className="saved-item-score">
                      부합도 {(item.score * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                <div className="saved-item-meta">
                  <span className="saved-item-date">
                    {new Date(item.created_at).toLocaleDateString('ko-KR')}
                  </span>
                  {editingMemoId === item.id ? (
                    <div className="memo-edit-row">
                      <input
                        className="memo-input"
                        value={editingMemoText}
                        onChange={e => setEditingMemoText(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleMemoSave(item.id)}
                        autoFocus
                      />
                      <button className="btn-memo-save" onClick={() => handleMemoSave(item.id)}>저장</button>
                      <button className="btn-memo-cancel" onClick={() => setEditingMemoId(null)}>취소</button>
                    </div>
                  ) : (
                    <span
                      className="saved-item-memo"
                      onClick={() => { setEditingMemoId(item.id); setEditingMemoText(item.memo ?? ''); }}
                      title="클릭하여 메모 편집"
                    >
                      {item.memo ? item.memo : <span className="memo-placeholder">메모 추가...</span>}
                    </span>
                  )}
                </div>
                <button
                  className="btn-delete-fixed"
                  onClick={() => handleDeleteFixed(item.id)}
                  title="삭제"
                >
                  ✕
                </button>
              </div>
            ))}
          </div>
        </div>
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

      {/* ── STEP 5: 실전 당첨 시뮬레이션 (탭) ── */}
      <section className="section real-sim-section">
        <h2 className="section-title">STEP 5 — 실전 당첨 시뮬레이션</h2>

        {/* 탭 헤더 */}
        <div className="step3-tabs">
          <button
            className={`step3-tab ${step5Tab === 'condition' ? 'active' : ''}`}
            onClick={() => setStep5Tab('condition')}
          >
            조건 기반 (단일 방법)
          </button>
          <button
            className={`step3-tab pattern-tab ${step5Tab === 'integrated' ? 'active' : ''}`}
            onClick={() => setStep5Tab('integrated')}
          >
            통합 비교 ★ (패턴 vs 조건 vs 랜덤)
          </button>
        </div>

        {/* ── 탭 1: 기존 단일 방법 시뮬레이션 ── */}
        {step5Tab === 'condition' && (
          <div className="step3-tab-content">
            <p className="section-desc">
              역대 각 회차마다 추천번호 N게임을 생성하고 실제 당첨번호와 대조합니다.
              랜덤 구매와 ROI를 비교해 전략의 실질적인 효과를 검증합니다.
              <br />
              <strong>주의:</strong> 처리 시간이 1~3분 소요될 수 있습니다.
            </p>

            <div className="config-row">
              <label>
                예측 방법
                <select
                  className="real-sim-select"
                  value={realSimMethod}
                  onChange={e => setRealSimMethod(e.target.value)}
                >
                  {(meta?.methods ?? ['FREQUENCY','WEIGHTED_RECENT','CYCLE','TREND','ENSEMBLE']).map(m => (
                    <option key={m} value={m}>{m} — {METHOD_DESC[m] ?? ''}</option>
                  ))}
                </select>
              </label>
              <label>
                게임 수 (회차당)
                <input type="number" min={1} max={20} value={realSimGames}
                  onChange={e => setRealSimGames(Number(e.target.value))} />
              </label>
              <label>
                샘플 간격 (N회 마다)
                <input type="number" min={1} max={50} value={realSimSampleEvery}
                  onChange={e => setRealSimSampleEvery(Number(e.target.value))} />
              </label>
            </div>

            <button
              className="btn-primary real-sim-run-btn"
              onClick={handleRealSim}
              disabled={realSimLoading}
            >
              {realSimLoading
                ? `시뮬레이션 실행 중... (1~3분 소요)`
                : `"${realSimMethod}" 실전 시뮬레이션 실행`}
            </button>
            {realSimError && <div className="error-msg">{realSimError}</div>}

            {realSimResult && (
              <div className="real-sim-result">
                <h3 className="chart-subtitle">
                  시뮬레이션 결과 — {realSimResult.method}
                  <span className="section-sub">
                    {realSimResult.tested_rounds}회차 검증 · 총 {realSimResult.total_games}게임
                  </span>
                </h3>
                <div className="stat-cards">
                  <div className="stat-card">
                    <div className="stat-label">총 투자금</div>
                    <div className="stat-value">{realSimResult.total_spent.toLocaleString()}원</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">총 당첨금</div>
                    <div className="stat-value">{realSimResult.total_prize.toLocaleString()}원</div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">순손익</div>
                    <div className={`stat-value ${realSimResult.net >= 0 ? 'positive' : 'negative'}`}>
                      {realSimResult.net >= 0 ? '+' : ''}{realSimResult.net.toLocaleString()}원
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-label">ROI</div>
                    <div className={`stat-value ${realSimResult.roi >= 0 ? 'positive' : 'negative'}`}>
                      {realSimResult.roi >= 0 ? '+' : ''}{realSimResult.roi.toFixed(1)}%
                    </div>
                  </div>
                </div>
                <h3 className="chart-subtitle">전략 vs 랜덤 비교</h3>
                <div className="sim-compare-table">
                  <div className="sim-compare-row sim-compare-header">
                    <div className="sim-compare-cell">항목</div>
                    <div className="sim-compare-cell highlight-cell">전략 ({realSimResult.method})</div>
                    <div className="sim-compare-cell">랜덤 구매</div>
                  </div>
                  <div className="sim-compare-row">
                    <div className="sim-compare-cell">ROI</div>
                    <div className={`sim-compare-cell highlight-cell ${realSimResult.roi >= realSimResult.random_roi ? 'positive' : 'negative'}`}>
                      {realSimResult.roi.toFixed(1)}%
                    </div>
                    <div className="sim-compare-cell">{realSimResult.random_roi.toFixed(1)}%</div>
                  </div>
                  <div className="sim-compare-row">
                    <div className="sim-compare-cell">순손익</div>
                    <div className={`sim-compare-cell highlight-cell ${realSimResult.net >= realSimResult.random_net ? 'positive' : 'negative'}`}>
                      {realSimResult.net.toLocaleString()}원
                    </div>
                    <div className="sim-compare-cell">{realSimResult.random_net.toLocaleString()}원</div>
                  </div>
                  {([1,2,3,4,5] as const).map(rank => (
                    <div key={rank} className="sim-compare-row">
                      <div className="sim-compare-cell">{rank}등 당첨</div>
                      <div className="sim-compare-cell highlight-cell">
                        {realSimResult.rank_counts[rank]}회 ({realSimResult.rank_rate[rank].toFixed(2)}%)
                      </div>
                      <div className="sim-compare-cell">
                        {realSimResult.random_counts[rank]}회 ({realSimResult.random_rate[rank].toFixed(2)}%)
                      </div>
                    </div>
                  ))}
                </div>
                <h3 className="chart-subtitle">등수별 당첨 분포</h3>
                <div className="rank-summary">
                  {([1,2,3,4,5] as const).map(rank => (
                    <div key={rank} className="rank-item">
                      <span className="rank-label">{rank}등</span>
                      <span className="rank-count">{realSimResult.rank_counts[rank]}</span>
                      <span className="rank-rate">{realSimResult.rank_rate[rank].toFixed(2)}%</span>
                    </div>
                  ))}
                  <div className="rank-item">
                    <span className="rank-label">낙첨</span>
                    <span className="rank-count">{realSimResult.rank_counts[0]}</span>
                    <span className="rank-rate">{realSimResult.rank_rate[0].toFixed(1)}%</span>
                  </div>
                </div>
                <button className="btn-toggle-detail" onClick={() => setShowDetail(v => !v)}>
                  {showDetail ? '▲ 회차별 상세 접기' : '▼ 회차별 상세 보기'}
                </button>
                {showDetail && (
                  <div className="real-sim-detail">
                    <h3 className="chart-subtitle">회차별 상세 결과 (당첨 회차만)</h3>
                    {realSimResult.detail.filter(d => d.rank > 0).length === 0 ? (
                      <p className="saved-empty">당첨된 회차가 없습니다.</p>
                    ) : (
                      <div className="hit-rounds-list">
                        {realSimResult.detail.filter(d => d.rank > 0).map((d, i) => (
                          <div key={i} className={`hit-round-item rank-${d.rank}`}>
                            <div className="hit-round-meta">
                              <span className="hit-round-no">{d.round}회</span>
                              <span className="hit-rank-badge" style={{ background: ['#e74c3c','#e67e22','#f1c40f','#2ecc71','#3498db'][d.rank - 1] ?? '#aaa' }}>
                                {d.rank}등
                              </span>
                              <span className="hit-round-date">매칭 {d.matched}개</span>
                            </div>
                            <div className="hit-round-balls">
                              <span style={{ fontSize: 11, color: '#aaa', marginRight: 6 }}>추천:</span>
                              {d.game.map(n => <LottoBall key={n} number={n} size="sm" />)}
                            </div>
                            <div className="hit-round-balls">
                              <span style={{ fontSize: 11, color: '#aaa', marginRight: 6 }}>실제:</span>
                              {d.actual.map(n => <LottoBall key={n} number={n} size="sm" />)}
                              {d.bonus != null && (<><span className="bonus-sep">+</span><LottoBall number={d.bonus} size="sm" /></>)}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* ── 탭 2: 통합 비교 시뮬레이션 (패턴 vs 조건 vs 랜덤) ── */}
        {step5Tab === 'integrated' && (
          <div className="step3-tab-content">
            <p className="section-desc">
              <strong>1회부터 전체 회차</strong>를 순회하며 세 가지 방식의 번호를 생성해 실제 당첨번호와 대조합니다.
              패턴 기반(합계 신호)·조건 기반(WEIGHTED_RECENT)·랜덤의 ROI와 당첨 횟수를 직접 비교합니다.
              <br />
              <strong>주의:</strong> sample_every=1이면 수 분 소요. 5~10 권장.
            </p>
            <div className="config-row">
              <label>
                게임 수 (회차당)
                <input type="number" min={1} max={20} value={simNGames}
                  onChange={e => setSimNGames(Number(e.target.value))} />
              </label>
              <label>
                샘플 간격
                <input type="number" min={1} max={100} value={simSampleEvery}
                  onChange={e => setSimSampleEvery(Number(e.target.value))} />
              </label>
              <label>
                조건 기반 학습 윈도우
                <input type="number" min={50} max={800} value={simCondWindow}
                  onChange={e => setSimCondWindow(Number(e.target.value))} />
              </label>
            </div>
            <button
              className="btn-primary btn-pattern real-sim-run-btn"
              onClick={handlePatternSim}
              disabled={patternSimLoading}
            >
              {patternSimLoading
                ? '통합 시뮬레이션 실행 중... (수 분 소요)'
                : `전체 회차 통합 시뮬레이션 실행 (${simNGames}게임 × 매 ${simSampleEvery}회)`}
            </button>
            {patternSimError && <div className="error-msg">{patternSimError}</div>}

            {patternSimResult && (() => {
              const { pattern, condition, random, tested_rounds, n_games, total_spent } = patternSimResult;
              const rows = [pattern, condition, random];
              const RANK_COLORS = ['#e74c3c','#e67e22','#f1c40f','#2ecc71','#3498db'];
              return (
                <div className="real-sim-result">
                  <h3 className="chart-subtitle">
                    통합 시뮬레이션 결과
                    <span className="section-sub">
                      {tested_rounds}회차 검증 · 회차당 {n_games}게임 · 총 투자 {total_spent.toLocaleString()}원
                    </span>
                  </h3>

                  {/* 3자 비교 테이블 */}
                  <div className="sim-compare-table">
                    <div className="sim-compare-row sim-compare-header">
                      <div className="sim-compare-cell">항목</div>
                      <div className="sim-compare-cell highlight-cell" style={{ color: '#e74c3c' }}>패턴 기반 ★</div>
                      <div className="sim-compare-cell" style={{ color: '#3498db' }}>조건 기반</div>
                      <div className="sim-compare-cell">랜덤</div>
                    </div>
                    <div className="sim-compare-row">
                      <div className="sim-compare-cell">ROI</div>
                      {rows.map((r, i) => (
                        <div key={i} className={`sim-compare-cell ${i === 0 ? 'highlight-cell' : ''} ${r.roi >= random.roi ? 'positive' : 'negative'}`}>
                          {r.roi >= 0 ? '+' : ''}{r.roi.toFixed(2)}%
                        </div>
                      ))}
                    </div>
                    <div className="sim-compare-row">
                      <div className="sim-compare-cell">순손익</div>
                      {rows.map((r, i) => (
                        <div key={i} className={`sim-compare-cell ${i === 0 ? 'highlight-cell' : ''} ${r.net >= 0 ? 'positive' : 'negative'}`}>
                          {r.net >= 0 ? '+' : ''}{r.net.toLocaleString()}원
                        </div>
                      ))}
                    </div>
                    {([3,4,5] as const).map(rank => (
                      <div key={rank} className="sim-compare-row">
                        <div className="sim-compare-cell">{rank}등 당첨</div>
                        {rows.map((r, i) => (
                          <div key={i} className={`sim-compare-cell ${i === 0 ? 'highlight-cell' : ''}`}>
                            {r.rank_counts[rank]}회 ({r.rank_rate[rank].toFixed(3)}%)
                          </div>
                        ))}
                      </div>
                    ))}
                    <div className="sim-compare-row">
                      <div className="sim-compare-cell">낙첨</div>
                      {rows.map((r, i) => (
                        <div key={i} className={`sim-compare-cell ${i === 0 ? 'highlight-cell' : ''}`}>
                          {r.rank_counts[0]}회 ({r.rank_rate[0].toFixed(1)}%)
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* 3개 방식 카드 */}
                  <h3 className="chart-subtitle">방식별 상세 요약</h3>
                  <div className="integrated-cards">
                    {rows.map((r, i) => (
                      <div key={i} className={`integrated-card ${i === 0 ? 'card-pattern' : i === 1 ? 'card-condition' : 'card-random'}`}>
                        <div className="integrated-card-title">{r.label}</div>
                        <div className={`integrated-card-roi ${r.roi >= 0 ? 'positive' : 'negative'}`}>
                          ROI {r.roi >= 0 ? '+' : ''}{r.roi.toFixed(2)}%
                        </div>
                        <div className="integrated-card-detail">
                          순손익 {r.net >= 0 ? '+' : ''}{r.net.toLocaleString()}원
                        </div>
                        <div className="integrated-card-ranks">
                          {([3,4,5] as const).map(rank => (
                            <span key={rank} className="rank-mini-badge" style={{ background: RANK_COLORS[rank - 1] }}>
                              {rank}등 {r.rank_counts[rank]}회
                            </span>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* 당첨 상세 */}
                  <button className="btn-toggle-detail" onClick={() => setShowSimDetail(v => !v)}>
                    {showSimDetail ? '▲ 당첨 회차 상세 접기' : `▼ 당첨 회차 상세 보기 (3등 이상, ${patternSimResult.detail.length}건)`}
                  </button>
                  {showSimDetail && (
                    <div className="real-sim-detail">
                      {patternSimResult.detail.length === 0 ? (
                        <p className="saved-empty">3등 이상 당첨 회차가 없습니다.</p>
                      ) : (
                        <div className="hit-rounds-list">
                          {patternSimResult.detail.map((d, i) => (
                            <div key={i} className="hit-round-item">
                              <div className="hit-round-meta">
                                <span className="hit-round-no">{d.round}회</span>
                                {d.pattern_rank >= 3 && (
                                  <span className="hit-rank-badge" style={{ background: RANK_COLORS[d.pattern_rank - 1] }}>
                                    패턴 {d.pattern_rank}등
                                  </span>
                                )}
                                {d.condition_rank >= 3 && (
                                  <span className="hit-rank-badge" style={{ background: '#3498db' }}>
                                    조건 {d.condition_rank}등
                                  </span>
                                )}
                                {d.target_sum_min != null && (
                                  <span className="rec-game-sum">
                                    합계타겟 {d.target_sum_min}~{d.target_sum_max}
                                  </span>
                                )}
                              </div>
                              {d.pattern_rank >= 3 && (
                                <div className="hit-round-balls">
                                  <span style={{ fontSize: 11, color: '#e74c3c', marginRight: 6 }}>패턴:</span>
                                  {d.pattern_game.map(n => <LottoBall key={n} number={n} size="sm" />)}
                                </div>
                              )}
                              {d.condition_rank >= 3 && (
                                <div className="hit-round-balls">
                                  <span style={{ fontSize: 11, color: '#3498db', marginRight: 6 }}>조건:</span>
                                  {d.condition_game.map(n => <LottoBall key={n} number={n} size="sm" />)}
                                </div>
                              )}
                              <div className="hit-round-balls">
                                <span style={{ fontSize: 11, color: '#aaa', marginRight: 6 }}>실제:</span>
                                {d.actual.map(n => <LottoBall key={n} number={n} size="sm" />)}
                                <span className="bonus-sep">+</span>
                                <LottoBall number={d.bonus} size="sm" />
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })()}
          </div>
        )}
      </section>
    </div>
  );
}
