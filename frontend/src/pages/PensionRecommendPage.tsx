import { useState } from 'react';
import { fetchPensionRecommend } from '../api/lottery';
import type { PensionRecommendResult, PensionGame } from '../types';
import './PensionRecommendPage.css';

const STRATEGY_LABEL: Record<string, string> = {
  frequency: '빈도 기반',
  balanced: '균형 기반',
  random: '무작위',
};

function GameCard({ game, idx }: { game: PensionGame; idx: number }) {
  return (
    <div className="pension-rec-game">
      <span className="rec-game-idx">{idx + 1}</span>
      <span className="rec-game-grp">{game.grp}조</span>
      <span className="rec-game-num">{String(game.num).padStart(6, '0')}</span>
      <span className="rec-game-strategy">{STRATEGY_LABEL[game.strategy] ?? game.strategy}</span>
    </div>
  );
}

function StrategySection({ title, data }: { title: string; data: { games: PensionGame[]; description: string } }) {
  return (
    <section className="rec-strategy-section">
      <h2 className="section-title">{title}</h2>
      <p className="rec-desc">{data.description}</p>
      <div className="rec-games-list">
        {data.games.map((g, i) => <GameCard key={i} game={g} idx={i} />)}
      </div>
    </section>
  );
}

export default function PensionRecommendPage() {
  const [result, setResult] = useState<PensionRecommendResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRecommend = () => {
    setLoading(true);
    setError(null);
    fetchPensionRecommend(3)
      .then(setResult)
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false));
  };

  return (
    <div className="pension-recommend-page">
      <h1 className="page-title">연금복권 번호 추천</h1>
      <p className="page-desc">과거 당첨 데이터 기반으로 3가지 전략의 번호를 추천합니다.</p>

      <button className="btn-recommend" onClick={handleRecommend} disabled={loading}>
        {loading ? '추천 중...' : '번호 추천받기'}
      </button>

      {error && <div className="page-error">{error}</div>}

      {result && (
        <div className="rec-results">
          <StrategySection title="빈도 기반 추천" data={result.frequency} />
          <StrategySection title="균형 기반 추천" data={result.balanced} />
          <StrategySection title="무작위 추천" data={result.random} />
        </div>
      )}
    </div>
  );
}
