import { useState, useEffect } from 'react';
import { fetchPatternAnalysis } from '../api/lottery';
import type { PatternAnalysisResult } from '../types';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Cell,
} from 'recharts';
import './PatternAnalysisPage.css';

// Gemini 자문 + 실데이터 분석 결과 요약
const AI_INSIGHTS = [
  {
    title: 'Gemini AI 자문 — 추천 신규 기법',
    items: [
      '합계 이동 방향 반전 (sum_direction): up→down 이후 다음 상승 63.5% — 가장 강한 신호',
      '극단 합계 평균회귀 (sum_reversion): 합계<100 또는 ≥180 이후 87%+ 중간 구간 진입',
      '2회 전 번호 재등장 (prev2_overlap): 1개 겹침 확률 44.8% vs 이론 42.4%',
      '소수 개수 (prime_count): 회차별 소수 번호 개수 분포 편향 여부',
      '최대 번호 간격 (gap_max): 번호 분포의 극단 집중/분산 측정',
      '번호 표준편차 구간 (std_dev_bucket): tight/mid/spread 분포 패턴',
    ],
    color: '#9b59b6',
  },
  {
    title: '패턴 없음 — 무시 권장',
    items: [
      '보너스 carry-over: 13.7% (이론값 13.3%와 동일, 완전 랜덤)',
      '홀짝 연속성: 이론값과 1% 이내 오차',
      '직전 회차 번호 중복: 이론값과 거의 동일',
      '5개 겹침 주기성: 19쌍 발견, 이론 기댓값(21.1)과 동일',
    ],
    color: '#e74c3c',
  },
];

export default function PatternAnalysisPage() {
  const [data, setData] = useState<PatternAnalysisResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = async () => {
    setLoading(true);
    setError('');
    try {
      const r = await fetchPatternAnalysis();
      setData(r);
    } catch {
      setError('분석 실패. 데이터를 먼저 수집하세요.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  // 합계 방향 반전 차트 데이터
  const directionChartData = data ? [
    {
      label: 'up→down 후 상승',
      actual: data.sum_direction.after_up_down_pct_up,
      theory: data.sum_direction.theory_pct,
    },
    {
      label: 'down→up 후 하락',
      actual: data.sum_direction.after_down_up_pct_down,
      theory: data.sum_direction.theory_pct,
    },
  ] : [];

  // prev2 carry 차트
  const prev2ChartData = data
    ? Object.entries(data.prev2_carry.distribution).map(([k, v]) => ({
        label: `${k}개 겹침`,
        actual: v.pct,
        theory: v.theory_pct ?? 0,
      }))
    : [];

  // 소수 개수 분포
  const primeChartData = data
    ? Object.entries(data.prime_count.distribution).map(([k, v]) => ({
        label: `소수 ${k}개`,
        count: v.pct,
      }))
    : [];

  // 최대 간격 분포 (상위 10개)
  const gapMaxData = data
    ? Object.entries(data.gap_max.distribution)
        .sort((a, b) => Number(a[0]) - Number(b[0]))
        .map(([k, v]) => ({ label: k, count: (v as any).pct }))
    : [];

  return (
    <div className="pattern-page">
      <h1 className="page-title">패턴 분석 — 실증 검증</h1>
      <p className="page-desc">
        1,213회차 데이터 + Gemini AI 자문을 바탕으로 2·3등 당첨에 영향을 줄 수 있는
        통계적 패턴을 분석합니다. 신뢰도 낮음을 전제하되, 이론값과 실제값의 차이를 시각화합니다.
      </p>

      {/* AI 자문 요약 */}
      <div className="ai-insight-grid">
        {AI_INSIGHTS.map((section, i) => (
          <div key={i} className="ai-insight-card" style={{ borderTop: `4px solid ${section.color}` }}>
            <h3 className="ai-insight-title" style={{ color: section.color }}>{section.title}</h3>
            <ul className="ai-insight-list">
              {section.items.map((item, j) => (
                <li key={j}>{item}</li>
              ))}
            </ul>
          </div>
        ))}
      </div>

      {loading && <div className="loading-msg">분석 중...</div>}
      {error && <div className="error-msg">{error}</div>}

      {data && (
        <>
          {/* 총 데이터 뱃지 */}
          <div className="data-badge">총 {data.total_draws.toLocaleString()}회차 분석</div>

          {/* ── 신호 A: 합계 방향 반전 ── */}
          <section className="section pattern-section-strong">
            <h2 className="section-title">
              신호 A — 합계 방향 반전 패턴
              <span className="signal-badge high">★★ 가장 강한 신호</span>
            </h2>
            <p className="section-desc">
              합계가 방향을 꺾은 직후(up→down 또는 down→up), 다음 회차에서 다시 꺾이는 경향.
              <br />
              즉 <strong>3연속 같은 방향이 드물다</strong> — 이를 이용해 다음 회차 합계 방향을 좁힐 수 있음.
            </p>
            <div className="signal-cards">
              <div className="signal-card">
                <div className="signal-label">up→down 이후 다음 상승</div>
                <div className="signal-value highlight">{data.sum_direction.after_up_down_pct_up}%</div>
                <div className="signal-theory">이론값: {data.sum_direction.theory_pct}%</div>
                <div className="signal-diff positive">+{(data.sum_direction.after_up_down_pct_up - data.sum_direction.theory_pct).toFixed(1)}%p</div>
                <div className="signal-n">n={data.sum_direction.after_up_down_n}회</div>
              </div>
              <div className="signal-card">
                <div className="signal-label">down→up 이후 다음 하락</div>
                <div className="signal-value highlight">{data.sum_direction.after_down_up_pct_down}%</div>
                <div className="signal-theory">이론값: {data.sum_direction.theory_pct}%</div>
                <div className="signal-diff positive">+{(data.sum_direction.after_down_up_pct_down - data.sum_direction.theory_pct).toFixed(1)}%p</div>
                <div className="signal-n">n={data.sum_direction.after_down_up_n}회</div>
              </div>
            </div>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={directionChartData} barGap={8}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis domain={[0, 80]} unit="%" tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => [`${v}%`]} />
                <ReferenceLine y={50} stroke="#e74c3c" strokeDasharray="4 4" label={{ value: '이론값 50%', fill: '#e74c3c', fontSize: 11 }} />
                <Bar dataKey="actual" name="실제" fill="#2980b9" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <p className="insight-text">{data.sum_direction.insight}</p>
          </section>

          {/* ── 신호 B: 극단 합계 평균 회귀 ── */}
          <section className="section pattern-section-strong">
            <h2 className="section-title">
              신호 B — 극단 합계 후 평균 회귀
              <span className="signal-badge high">★★ 강한 신호</span>
            </h2>
            <p className="section-desc">
              합계가 극단값(&lt;100 또는 ≥180)이었던 회차 이후, 다음 회차는 압도적으로 중간 구간(100-179)에 진입.
              <br />
              극단 합계가 나왔을 때 <strong>다음 회차는 중간 합계 번호에 집중</strong>하는 전략 근거.
            </p>
            <div className="signal-cards">
              <div className="signal-card">
                <div className="signal-label">극단 회차 수</div>
                <div className="signal-value">{data.sum_reversion.extreme_count}회</div>
                <div className="signal-theory">전체의 {(data.sum_reversion.extreme_count / data.total_draws * 100).toFixed(1)}%</div>
              </div>
              <div className="signal-card">
                <div className="signal-label">극단 이후 중간 합계 진입</div>
                <div className="signal-value highlight">{data.sum_reversion.after_extreme_pct_normal}%</div>
                <div className="signal-theory">전체 중간 합계 비율: {data.sum_reversion.theory_normal_pct}%</div>
                <div className="signal-diff positive">+{(data.sum_reversion.after_extreme_pct_normal - data.sum_reversion.theory_normal_pct).toFixed(1)}%p</div>
              </div>
              <div className="signal-card">
                <div className="signal-label">극단 이후 재극단</div>
                <div className="signal-value">{data.sum_reversion.after_extreme_pct_extreme}%</div>
                <div className="signal-theory">드묾 (평균회귀)</div>
              </div>
            </div>
            <p className="insight-text">{data.sum_reversion.insight}</p>
          </section>

          {/* ── 신호 C: 2회 전 번호 재등장 ── */}
          <section className="section">
            <h2 className="section-title">
              신호 C — 2회 전 번호 재등장 확률
              <span className="signal-badge mid">★ 약한 신호</span>
            </h2>
            <p className="section-desc">
              2회차 전 당첨번호와 현재 번호의 겹침 분포. 0개 겹침이 이론보다 적고, 1개 겹침이 이론보다 많음.
              <br />
              2회 전 번호를 일부 포함하는 전략이 순수 랜덤 대비 미세하게 유리할 수 있음.
            </p>
            <ResponsiveContainer width="100%" height={220}>
              <BarChart data={prev2ChartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 12 }} />
                <YAxis unit="%" domain={[0, 50]} tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => [`${v.toFixed(1)}%`]} />
                <Bar dataKey="actual" name="실제" radius={[4, 4, 0, 0]}>
                  {prev2ChartData.map((entry, i) => {
                    const diff = entry.actual - entry.theory;
                    return <Cell key={i} fill={diff > 1 ? '#27ae60' : diff < -1 ? '#e74c3c' : '#95a5a6'} />;
                  })}
                </Bar>
                <Bar dataKey="theory" name="이론값" fill="#ecf0f1" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
            <p className="insight-text">{data.prev2_carry.insight}</p>
          </section>

          {/* ── 신규 조건 분포 ── */}
          <div className="two-col-grid">
            {/* 소수 개수 */}
            <section className="section">
              <h2 className="section-title">소수 개수 분포 (prime_count)</h2>
              <p className="section-desc">
                실제 평균: <strong>{data.prime_count.avg}</strong>개 / 이론 평균: {data.prime_count.theory_avg}개
                (차이: {data.prime_count.diff > 0 ? '+' : ''}{data.prime_count.diff})
              </p>
              <ResponsiveContainer width="100%" height={180}>
                <BarChart data={primeChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" tick={{ fontSize: 11 }} />
                  <YAxis unit="%" tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number) => [`${v.toFixed(1)}%`]} />
                  <Bar dataKey="count" name="비율" fill="#8e44ad" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </section>

            {/* 번호 분산 구간 */}
            <section className="section">
              <h2 className="section-title">번호 분산 구간 (std_dev_bucket)</h2>
              <p className="section-desc">tight(표준편차&lt;10) / mid(10-16) / spread(&gt;16)</p>
              <div className="dist-bars">
                {Object.entries(data.std_dev_bucket.distribution).map(([k, v]) => (
                  <div key={k} className="dist-bar-row">
                    <span className="dist-bar-label">{k}</span>
                    <div className="dist-bar-track">
                      <div
                        className="dist-bar-fill"
                        style={{ width: `${v.pct}%`, background: k === 'mid' ? '#2980b9' : k === 'tight' ? '#27ae60' : '#e67e22' }}
                      />
                    </div>
                    <span className="dist-bar-pct">{v.pct.toFixed(1)}%</span>
                    <span className="dist-bar-count">({v.count}회)</span>
                  </div>
                ))}
              </div>
              <p className="insight-text">{data.std_dev_bucket.insight}</p>
            </section>
          </div>

          {/* 최대 번호 간격 */}
          <section className="section">
            <h2 className="section-title">최대 번호 간격 분포 (gap_max)</h2>
            <p className="section-desc">
              6개 번호 중 인접 번호 간 최대 간격. 평균: <strong>{data.gap_max.avg}</strong>
            </p>
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={gapMaxData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" tick={{ fontSize: 10 }} />
                <YAxis unit="%" tick={{ fontSize: 11 }} />
                <Tooltip formatter={(v: number) => [`${v.toFixed(1)}%`]} />
                <Bar dataKey="count" name="비율" fill="#16a085" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </section>

          {/* ── 패턴 없음 확인 ── */}
          <section className="section no-signal-section">
            <h2 className="section-title">패턴 없음 — 실증 확인</h2>
            <div className="no-signal-grid">
              <div className="no-signal-card">
                <div className="no-signal-title">보너스 carry-over</div>
                <div className="no-signal-values">
                  <span className="ns-actual">실제 {data.bonus_carryover.pct}%</span>
                  <span className="ns-theory">이론 {data.bonus_carryover.theory_pct}%</span>
                </div>
                <div className="no-signal-verdict">패턴 없음</div>
                <p className="insight-text small">{data.bonus_carryover.insight}</p>
              </div>
              <div className="no-signal-card">
                <div className="no-signal-title">합계+홀수 조합 지속성 (1회 후)</div>
                <div className="no-signal-values">
                  <span className="ns-actual">실제 {data.consecutive_sum.same_1lag_pct}%</span>
                  <span className="ns-theory">이론 {data.consecutive_sum.theory_pct}%</span>
                </div>
                <div className={`no-signal-verdict ${Math.abs(data.consecutive_sum.diff) > 1 ? 'weak-signal' : ''}`}>
                  {Math.abs(data.consecutive_sum.diff) > 1 ? `약한 신호 (+${data.consecutive_sum.diff}%p)` : '미미한 차이'}
                </div>
                <p className="insight-text small">{data.consecutive_sum.insight}</p>
              </div>
            </div>
          </section>

          {/* ── 결론 및 전략 ── */}
          <section className="section conclusion-section">
            <h2 className="section-title">분석 결론 및 실전 활용 전략</h2>
            <div className="conclusion-list">
              <div className="conclusion-item strong">
                <span className="con-icon">1</span>
                <div>
                  <strong>직전 합계가 극단(&lt;100 또는 ≥180)이면</strong> — 다음 회차는 합계 120-159 범위 번호에 집중.
                  극단 이후 재극단 확률 낮음.
                </div>
              </div>
              <div className="conclusion-item strong">
                <span className="con-icon">2</span>
                <div>
                  <strong>직전 합계가 up이고 그 전도 up이었다면</strong> — 이번은 합계 낮은 방향 선호.
                  (연속 상승 이후 반전 63.5%)
                </div>
              </div>
              <div className="conclusion-item weak">
                <span className="con-icon">3</span>
                <div>
                  <strong>2회 전 번호 1~2개를 포함</strong>하면 순수 랜덤 대비 미세하게 유리.
                  (이론 40% → 실제 37%로 완전 비포함이 드묾)
                </div>
              </div>
              <div className="conclusion-item note">
                <span className="con-icon">!</span>
                <div>
                  위 신호들은 <strong>통계적으로 유의하지 않을 수 있음</strong>. 1,213회차는
                  패턴 검출에 충분하지 않으며, 진짜 패턴이 없을 가능성이 높음.
                  단, 이론값 대비 이탈이 지속된다면 활용 여지 있음.
                </div>
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}
