import { useState } from 'react';
import { recommend } from '../api/lottery';
import type { AllRecommendResult, RecommendResult } from '../types';
import LottoBall from '../components/LottoBall';
import './RecommendPage.css';

const STRATEGY_LABELS: Record<string, string> = {
  smart:     '스마트 추천',
  frequency: '빈도 기반',
  trend:     '트렌드 기반',
  balanced:  '균형 추천',
  random:    '완전 랜덤',
};

const STRATEGY_DESC: Record<string, string> = {
  smart:     '백테스트 기반 조건 예측 결과를 바탕으로, 서로 지나치게 겹치지 않게 조합을 다시 정렬합니다.',
  frequency: '역대 출현 빈도가 높은 번호에 높은 가중치를 부여합니다.',
  trend:     '최근 N회에서 상대적으로 자주 나온 번호를 우선합니다.',
  balanced:  '홀/짝, 고/저, 구간 분산을 맞춘 균형 조합입니다.',
  random:    '완전 무작위로 선택합니다.',
};

function GameCard({ game, idx }: { game: { numbers: number[]; strategy: string }; idx: number }) {
  return (
    <div className="game-card">
      <div className="game-label">게임 {idx + 1}</div>
      <div className="game-balls">
        {game.numbers.map(n => <LottoBall key={n} number={n} size="lg" />)}
      </div>
    </div>
  );
}

function StrategyResult({ strategy, result }: { strategy: string; result: RecommendResult }) {
  return (
    <section className="strategy-section">
      <div className="strategy-header">
        <h3>{STRATEGY_LABELS[strategy] ?? strategy}</h3>
        <p className="strategy-desc">{STRATEGY_DESC[strategy] ?? result.description}</p>
      </div>
      <div className="games-grid">
        {result.games.map((g, i) => <GameCard key={i} game={g} idx={i} />)}
      </div>
    </section>
  );
}

export default function RecommendPage() {
  const [games, setGames] = useState(5);
  const [recentN, setRecentN] = useState(50);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<AllRecommendResult | null>(null);
  const [error, setError] = useState('');

  const handleRecommend = async () => {
    setLoading(true);
    setError('');
    try {
      const data = await recommend({ strategy: 'all', games, recent_n: recentN });
      setResult(data as AllRecommendResult);
    } catch {
      setError('번호 추천 중 오류가 발생했습니다. 데이터를 먼저 수집하세요.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="recommend-page">
      <h1 className="page-title">번호 추천</h1>

      <section className="section config-section">
        <div className="config-row">
          <label>
            게임 수
            <input
              type="number"
              min={1} max={20}
              value={games}
              onChange={e => setGames(Number(e.target.value))}
            />
          </label>
          <label>
            트렌드 기준 회차
            <input
              type="number"
              min={10} max={200}
              value={recentN}
              onChange={e => setRecentN(Number(e.target.value))}
            />
          </label>
          <button className="btn-primary" onClick={handleRecommend} disabled={loading}>
            {loading ? '생성 중...' : '번호 추천받기'}
          </button>
        </div>
        {error && <div className="error-msg">{error}</div>}
      </section>

      {result && (
        <div className="result-area">
          {Object.entries(result).map(([strategy, data]) => (
            <StrategyResult key={strategy} strategy={strategy} result={data as RecommendResult} />
          ))}
        </div>
      )}
    </div>
  );
}
