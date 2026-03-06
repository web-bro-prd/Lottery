import { useEffect, useState } from 'react';
import { fetchWeeklyHistory } from '../api/lottery';
import type { WeeklyHistoryRecord, WeeklyHistoryResultDetail } from '../types';
import LottoBall from '../components/LottoBall';
import './WeeklyHistoryPage.css';

const RANK_LABEL: Record<number, string> = {
  1: '1등', 2: '2등', 3: '3등', 4: '4등', 5: '5등', 0: '낙첨',
};
const RANK_CLASS: Record<number, string> = {
  1: 'rank-1', 2: 'rank-2', 3: 'rank-3', 4: 'rank-4', 5: 'rank-5', 0: 'rank-0',
};

function GameRow({ detail, idx }: { detail: WeeklyHistoryResultDetail; idx: number }) {
  const rank = detail.rank;
  return (
    <div className={`game-row ${RANK_CLASS[rank] ?? 'rank-0'}`}>
      <span className="game-idx">{idx + 1}</span>
      <span className={`game-source ${detail.is_fixed ? 'fixed-tag' : ''}`}>
        {detail.is_fixed ? '고정' : detail.source_label || '추천'}
      </span>
      <div className="game-balls">
        {detail.game.map((n, i) => (
          <LottoBall key={i} number={n} size="sm" />
        ))}
      </div>
      <span className={`game-rank ${RANK_CLASS[rank] ?? 'rank-0'}`}>
        {RANK_LABEL[rank] ?? '낙첨'}
      </span>
      {rank > 0 && (
        <span className="game-matched">{detail.matched}개 일치</span>
      )}
    </div>
  );
}

function HistoryCard({ rec }: { rec: WeeklyHistoryRecord }) {
  const [expanded, setExpanded] = useState(false);
  const hasResult = !!rec.result_detail;
  const allGames = rec.result_detail ?? [];
  const bestRank = hasResult
    ? Math.min(...allGames.filter(r => r.rank > 0).map(r => r.rank).concat([999]))
    : null;
  const bestRankLabel = bestRank && bestRank < 999 ? RANK_LABEL[bestRank] : '낙첨';
  const bestRankClass = bestRank && bestRank < 999 ? RANK_CLASS[bestRank] : 'rank-0';

  return (
    <div className={`history-card ${hasResult ? 'has-result' : 'no-result'}`}>
      <div className="history-card-header" onClick={() => setExpanded(e => !e)}>
        <div className="history-card-title">
          <span className="history-round">{rec.target_round}회</span>
          <span className="history-date">{rec.sent_at?.slice(0, 10)}</span>
          {hasResult ? (
            <span className={`history-best-rank ${bestRankClass}`}>{bestRankLabel}</span>
          ) : (
            <span className="history-pending">결과 대기중</span>
          )}
        </div>
        {hasResult && rec.actual_numbers && (
          <div className="history-actual">
            <span className="history-actual-label">실제 당첨:</span>
            <div className="history-actual-balls">
              {rec.actual_numbers.map((n, i) => (
                <LottoBall key={i} number={n} size="sm" />
              ))}
              {rec.actual_bonus != null && (
                <LottoBall number={rec.actual_bonus} bonus size="sm" />
              )}
            </div>
          </div>
        )}
        <span className="expand-icon">{expanded ? '▲' : '▼'}</span>
      </div>

      {expanded && hasResult && (
        <div className="history-card-body">
          {allGames.map((d, i) => (
            <GameRow key={i} detail={d} idx={i} />
          ))}
        </div>
      )}
      {expanded && !hasResult && (
        <div className="history-card-body">
          {/* 추천게임 목록만 표시 (결과 없음) */}
          {[rec.fixed, ...rec.games].map((game, i) => (
            <div className="game-row rank-0" key={i}>
              <span className="game-idx">{i + 1}</span>
              <span className={`game-source ${i === 0 ? 'fixed-tag' : ''}`}>
                {i === 0 ? '고정' : (rec.source_labels?.[i] || '추천')}
              </span>
              <div className="game-balls">
                {game.map((n: number, j: number) => (
                  <LottoBall key={j} number={n} size="sm" />
                ))}
              </div>
              <span className="game-rank rank-0">미확인</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function WeeklyHistoryPage() {
  const [records, setRecords] = useState<WeeklyHistoryRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchWeeklyHistory()
      .then(res => setRecords(res.records))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page-loading">불러오는 중...</div>;
  if (error) return <div className="page-error">{error}</div>;

  const latest = records[0] ?? null;
  const history = records.slice(1);

  return (
    <div className="weekly-history-page">
      <h1 className="page-title">이번 주 추천번호</h1>

      {/* ── 이번 주 추천 크게 표시 ── */}
      {latest ? (
        <section className="this-week-section">
          <div className="this-week-round-badge">{latest.target_round}회</div>
          <div className="this-week-games">
            {/* 고정 */}
            <div className="this-week-game fixed-game">
              <span className="tw-game-label fixed-tag">고정</span>
              <div className="tw-balls">
                {latest.fixed.map((n, i) => (
                  <LottoBall key={i} number={n} size="lg" />
                ))}
              </div>
            </div>
            {/* 추천 9게임 */}
            {latest.games.map((game, i) => (
              <div className="this-week-game" key={i}>
                <span className="tw-game-label">
                  {latest.source_labels?.[i + 1] || `추천 ${i + 1}`}
                </span>
                <div className="tw-balls">
                  {game.map((n: number, j: number) => (
                    <LottoBall key={j} number={n} size="lg" />
                  ))}
                </div>
              </div>
            ))}
          </div>
          <div className="this-week-info">
            추천일: {latest.sent_at?.slice(0, 10)} &nbsp;|&nbsp;
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
              <HistoryCard key={rec.id} rec={rec} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}
