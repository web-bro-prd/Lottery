import { useEffect, useState } from 'react';
import { fetchPensionWeeklyHistory } from '../api/lottery';
import type { PensionWeeklyHistoryRecord, PensionGame, PensionWeeklyResultDetail } from '../types';
import './PensionWeeklyHistoryPage.css';

const RANK_LABEL: Record<number, string> = {
  1: '1등', 2: '2등', 3: '3등', 4: '4등', 5: '5등', 6: '6등', 7: '7등', 0: '낙첨',
};
const RANK_CLASS: Record<number, string> = {
  1: 'rank-1', 2: 'rank-2', 3: 'rank-3', 4: 'rank-4',
  5: 'rank-5', 6: 'rank-6', 7: 'rank-7', 0: 'rank-0',
};

const STRATEGY_LABEL: Record<string, string> = {
  frequency: '빈도',
  balanced: '균형',
  random: '랜덤',
};

function PensionGameBadge({ game }: { game: PensionGame }) {
  return (
    <span className="pension-game-badge">
      <span className="pg-grp">{game.grp}조</span>
      <span className="pg-num">{String(game.num).padStart(6, '0')}</span>
      {game.strategy && (
        <span className="pg-strategy">{STRATEGY_LABEL[game.strategy] ?? game.strategy}</span>
      )}
    </span>
  );
}

function PensionHistoryCard({ rec }: { rec: PensionWeeklyHistoryRecord }) {
  const [expanded, setExpanded] = useState(false);
  const hasResult = !!rec.result_detail;
  const bestRank = hasResult
    ? Math.min(...(rec.result_detail ?? []).filter(r => r.rank > 0).map(r => r.rank).concat([999]))
    : null;
  const bestRankLabel = bestRank && bestRank < 999 ? RANK_LABEL[bestRank] : '낙첨';
  const bestRankClass = bestRank && bestRank < 999 ? RANK_CLASS[bestRank] : 'rank-0';

  return (
    <div className={`pension-history-card ${hasResult ? 'has-result' : 'no-result'}`}>
      <div className="pension-card-header" onClick={() => setExpanded(e => !e)}>
        <div className="pension-card-title">
          <span className="pension-history-round">{rec.target_round}회</span>
          <span className="pension-history-date">{rec.sent_at?.slice(0, 10)}</span>
          {hasResult ? (
            <span className={`pension-best-rank ${bestRankClass}`}>{bestRankLabel}</span>
          ) : (
            <span className="history-pending">결과 대기중</span>
          )}
        </div>
        {hasResult && rec.actual_grp != null && rec.actual_num && (
          <div className="pension-actual">
            <span className="pension-actual-label">실제 당첨:</span>
            <span className="pension-actual-val">
              <strong>{rec.actual_grp}조</strong> {String(rec.actual_num).padStart(6, '0')}
              {rec.actual_bonus && (
                <span className="pension-actual-bonus"> / 보너스 {String(rec.actual_bonus).padStart(6, '0')}</span>
              )}
            </span>
          </div>
        )}
        <span className="expand-icon">{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && (
        <div className="pension-card-body">
          {hasResult
            ? (rec.result_detail as PensionWeeklyResultDetail[]).map((d, i) => (
                <div className={`pension-game-row ${RANK_CLASS[d.rank] ?? 'rank-0'}`} key={i}>
                  <span className="pg-idx">{i + 1}</span>
                  <PensionGameBadge game={d.game} />
                  <span className={`pg-rank ${RANK_CLASS[d.rank] ?? 'rank-0'}`}>
                    {RANK_LABEL[d.rank] ?? '낙첨'}
                  </span>
                </div>
              ))
            : (rec.games as PensionGame[]).map((g, i) => (
                <div className="pension-game-row rank-0" key={i}>
                  <span className="pg-idx">{i + 1}</span>
                  <PensionGameBadge game={g} />
                  <span className="pg-rank rank-0">미확인</span>
                </div>
              ))
          }
        </div>
      )}
    </div>
  );
}

export default function PensionWeeklyHistoryPage() {
  const [records, setRecords] = useState<PensionWeeklyHistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchPensionWeeklyHistory()
      .then(res => setRecords(res.records))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">불러오는 중...</div>;
  if (error) return <div className="page-error">{error}</div>;

  const latest = records[0] ?? null;
  const history = records.slice(1);

  return (
    <div className="pension-weekly-history-page">
      <h1 className="page-title">연금복권 이번 주 추천번호</h1>

      {/* ── 이번 주 추천 크게 표시 ── */}
      {latest ? (
        <section className="pension-this-week-section">
          <div className="pension-this-week-badge">{latest.target_round}회</div>
          <div className="pension-this-week-games">
            {(latest.games as PensionGame[]).map((g, i) => (
              <div className="pension-tw-game" key={i}>
                <span className="pension-tw-idx">{i + 1}</span>
                <span className="pension-tw-grp">{g.grp}조</span>
                <span className="pension-tw-num">{String(g.num).padStart(6, '0')}</span>
                <span className="pension-tw-strategy">
                  {STRATEGY_LABEL[g.strategy] ?? g.strategy}
                </span>
              </div>
            ))}
          </div>
          <div className="pension-this-week-info">
            추천일: {latest.sent_at?.slice(0, 10)} &nbsp;|&nbsp;
            매주 목요일 추첨 &nbsp;|&nbsp;
            {latest.result_detail ? '결과 확인됨' : '결과 대기중'}
          </div>
        </section>
      ) : (
        <div className="empty-msg">아직 추천번호가 없습니다.</div>
      )}

      {/* ── 히스토리 목록 ── */}
      {history.length > 0 && (
        <section className="history-section">
          <h2 className="section-title">지난 주 히스토리</h2>
          <div className="history-list">
            {history.map(rec => (
              <PensionHistoryCard key={rec.id} rec={rec} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
