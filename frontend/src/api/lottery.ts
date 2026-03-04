import client from './client';
import type {
  DrawsResponse,
  DrawResult,
  FullStats,
  FrequencyMap,
  TrendAnalysis,
  SimulateResult,
  MonteCarloResult,
  RecommendResult,
  AllRecommendResult,
  ServerStatus,
  BacktestMethodsResponse,
  BacktestResult,
  BacktestCumulativeResult,
  BacktestRecommendResult,
  FixedNumberResult,
  SavedFixedNumber,
  RealSimResult,
  PatternAnalysisResult,
  PatternRecommendResult,
  PatternSimResult,
} from '../types';

// ───────── 상태 ─────────
export const fetchStatus = (): Promise<ServerStatus> =>
  client.get('/status').then(r => r.data);

// ───────── 데이터 수집 ─────────
export const collectLatest = (): Promise<{ status: string; db_latest_round: number; message: string }> =>
  client.post('/collect/latest').then(r => r.data);

export const collectSingle = (round: number): Promise<{ status: string; data: DrawResult }> =>
  client.post(`/collect/round/${round}`).then(r => r.data);

export const uploadCsv = (file: File): Promise<{ status: string; success: number; fail: number }> => {
  const form = new FormData();
  form.append('file', file);
  return client.post('/collect/upload-csv', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};

export const uploadXlsx = (file: File): Promise<{ status: string; filename: string; success: number; fail: number }> => {
  const form = new FormData();
  form.append('file', file);
  return client.post('/collect/upload-xlsx', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  }).then(r => r.data);
};

// ───────── 당첨 번호 ─────────
export const fetchDraws = (start?: number, end?: number): Promise<DrawsResponse> => {
  const params: Record<string, number> = {};
  if (start) params.start = start;
  if (end) params.end = end;
  return client.get('/draws', { params }).then(r => r.data);
};

export const fetchLatestDraws = (): Promise<{ draws: DrawResult[] }> =>
  client.get('/draws/latest').then(r => r.data);

export const fetchDraw = (round: number): Promise<DrawResult> =>
  client.get(`/draws/${round}`).then(r => r.data);

// ───────── 통계 ─────────
export const fetchStats = (start?: number, end?: number): Promise<FullStats> => {
  const params: Record<string, number> = {};
  if (start) params.start = start;
  if (end) params.end = end;
  return client.get('/stats', { params }).then(r => r.data);
};

export const fetchFrequency = (start?: number, end?: number): Promise<FrequencyMap> => {
  const params: Record<string, number> = {};
  if (start) params.start = start;
  if (end) params.end = end;
  return client.get('/stats/frequency', { params }).then(r => r.data);
};

export const fetchTrend = (recentN = 50): Promise<TrendAnalysis> =>
  client.get('/stats/trend', { params: { recent_n: recentN } }).then(r => r.data);

// ───────── 시뮬레이션 ─────────
export const simulateRandom = (params: {
  games_per_round?: number;
  start_round?: number;
  end_round?: number;
}): Promise<SimulateResult> =>
  client.post('/simulate/random', params).then(r => r.data);

export const simulateStrategy = (params: {
  strategy_numbers: number[][];
  start_round?: number;
  end_round?: number;
}): Promise<SimulateResult> =>
  client.post('/simulate/strategy', params).then(r => r.data);

export const simulateMonteCarlo = (params: {
  games?: number;
  trials?: number;
}): Promise<MonteCarloResult> =>
  client.post('/simulate/montecarlo', params).then(r => r.data);

// ───────── 번호 추천 ─────────
export const recommend = (params: {
  strategy?: string;
  games?: number;
  recent_n?: number;
}): Promise<AllRecommendResult | RecommendResult> =>
  client.post('/recommend', params).then(r => r.data);

// ───────── 백테스팅 ─────────
export const fetchBacktestMethods = (): Promise<BacktestMethodsResponse> =>
  client.get('/backtest/methods').then(r => r.data);

export const runBacktest = (params: {
  window?: number;
  methods?: string[];
  sample_every?: number;
}): Promise<BacktestResult> =>
  client.post('/backtest/run', params).then(r => r.data);

export const runBacktestCumulative = (params: {
  window?: number;
  methods?: string[];
  sample_every?: number;
}): Promise<BacktestCumulativeResult> =>
  client.post('/backtest/cumulative', params).then(r => r.data);

export const runBacktestRecommend = (params: {
  method: string;
  window?: number;
  n_games?: number;
  condition_weights?: Record<string, number>;
}): Promise<BacktestRecommendResult> =>
  client.post('/backtest/recommend', params).then(r => r.data);

export const fetchFixedNumber = (): Promise<FixedNumberResult> =>
  client.get('/backtest/fixed').then(r => r.data);

export const runRealSim = (params: {
  method?: string;
  window?: number;
  n_games?: number;
  sample_every?: number;
}): Promise<RealSimResult> =>
  client.post('/backtest/real-sim', null, { params }).then(r => r.data);

// ───────── 고정번호 저장/관리 ─────────
export const getFixedNumbers = (): Promise<SavedFixedNumber[]> =>
  client.get('/fixed').then(r => r.data.fixed_numbers);

export const saveFixedNumber = (params: {
  numbers: number[];
  score?: number;
  rationale?: Record<string, string>;
  memo?: string;
}): Promise<SavedFixedNumber> =>
  client.post('/fixed', params).then(r => r.data);

export const deleteFixedNumber = (id: number): Promise<{ status: string }> =>
  client.delete(`/fixed/${id}`).then(r => r.data);

export const updateFixedMemo = (id: number, memo: string): Promise<SavedFixedNumber> =>
  client.patch(`/fixed/${id}/memo`, { memo }).then(r => r.data);

// ───────── 패턴 분석 ─────────
export const fetchPatternAnalysis = (): Promise<PatternAnalysisResult> =>
  client.get('/backtest/pattern-analysis').then(r => r.data);

// ───────── 패턴 기반 번호 추천 ─────────
export const runPatternRecommend = (nGames: number = 9): Promise<PatternRecommendResult> =>
  client.post('/backtest/pattern-recommend', null, { params: { n_games: nGames } }).then(r => r.data);

// ───────── 통합 시뮬레이션 (패턴 vs 조건 vs 랜덤) ─────────
export const runPatternSim = (params: {
  n_games?: number;
  sample_every?: number;
  condition_window?: number;
}): Promise<PatternSimResult> =>
  client.post('/backtest/pattern-sim', null, { params }).then(r => r.data);
