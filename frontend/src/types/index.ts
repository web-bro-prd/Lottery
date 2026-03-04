// ───────── 당첨 데이터 ─────────
export interface DrawResult {
  round: number;
  draw_date: string;
  num1: number;
  num2: number;
  num3: number;
  num4: number;
  num5: number;
  num6: number;
  bonus: number;
  total_prize: number | null;
  win1_count: number | null;
  win1_prize: number | null;
}

export interface DrawsResponse {
  total: number;
  draws: DrawResult[];
}

// ───────── 통계 ─────────
export interface NumberStat {
  count: number;
  frequency: number;
  rank: number;
}

export interface FrequencyMap {
  [key: string]: NumberStat;
}

export interface PatternStat {
  count: number;
  frequency: number;
}

export interface OddEvenDistribution {
  patterns: Record<string, PatternStat>;
}

export interface SumBucket {
  count: number;
  frequency: number;
}

export interface SumDistribution {
  average: number;
  min: number;
  max: number;
  buckets: Record<string, SumBucket>;
  raw: Record<string, number>;
}

export interface ZoneFreqItem {
  total: number;
  avg_per_draw: number;
  share: number;
}

export interface ZoneDistribution {
  zone_frequency: Record<string, ZoneFreqItem>;
  top_patterns: Array<{ pattern: string; count: number; frequency: number }>;
}

export interface TrendItem {
  number: number;
  all_frequency: number;
  recent_frequency: number;
  diff: number;
}

export interface TrendAnalysis {
  recent_n: number;
  hot_numbers: TrendItem[];
  cold_numbers: TrendItem[];
}

export interface PairFrequency {
  pair: [number, number];
  count: number;
  frequency: number;
}

export interface TripleFrequency {
  triple: [number, number, number];
  count: number;
  frequency: number;
}

export interface FullStats {
  total_draws: number;
  latest_round: number;
  frequency: FrequencyMap;
  bonus_frequency: FrequencyMap;
  odd_even: OddEvenDistribution;
  high_low: OddEvenDistribution;
  sum_dist: SumDistribution;
  consecutive: { patterns: Record<string, PatternStat> };
  zone: ZoneDistribution;
  last_digit: Record<string, PatternStat>;
  pair_frequency: PairFrequency[];
  triple_frequency: TripleFrequency[];
  trend: TrendAnalysis;
}

// ───────── 시뮬레이션 ─────────
export interface SimulateRoundDetail {
  round: number;
  spent: number;
  prize: number;
}

export interface SimulateResult {
  type: string;
  rounds_played: number;
  games_per_round: number;
  total_spent: number;
  total_prize: number;
  net: number;
  roi: number;
  rank_summary: Record<string, number>;
  detail: SimulateRoundDetail[];
}

export interface MonteCarloResult {
  games: number;
  trials: number;
  avg_roi: number;
  min_roi: number;
  max_roi: number;
  roi_distribution: number[];
}

// ───────── 추천 ─────────
export interface RecommendGame {
  numbers: number[];
  strategy: string;
}

export interface RecommendResult {
  games: RecommendGame[];
  strategy: string;
  description: string;
}

export interface AllRecommendResult {
  frequency: RecommendResult;
  trend: RecommendResult;
  balanced: RecommendResult;
  random: RecommendResult;
}

// ───────── 서버 상태 ─────────
export interface ServerStatus {
  total_rounds: number;
  latest_round: number | null;
  latest_date: string | null;
}

// ───────── 백테스팅 ─────────
export interface ConditionInfo {
  key: string;
  label: string;
}

export interface BacktestMethodsResponse {
  methods: string[];
  conditions: ConditionInfo[];
}

export interface MethodResult {
  avg_accuracy: number;
  condition_accuracy: Record<string, number>;
}

export interface BacktestResult {
  total_tested: number;
  window: number;
  best_method: string;
  ranking: [string, number][];
  condition_accuracy_avg: Record<string, number>;
  condition_labels: Record<string, string>;
  methods: Record<string, MethodResult>;
}

export interface BacktestCumulativeResult {
  rounds: number[];
  series: Record<string, number[]>;
  labels: Record<string, string>;
}

export interface BacktestRecommendResult {
  predicted_conditions: Record<string, string>;
  condition_labels: Record<string, string>;
  games: number[][];
  scores: number[];
  method: string;
  window: number;
  n_games: number;
}

export interface FixedNumberResult {
  numbers: number[];
  score: number;
  rationale: Record<string, string>;
  all_conditions: Record<string, string>;
  target_conditions: Record<string, string>;
  condition_labels: Record<string, string>;
  median_sum: number;
}

export interface SavedFixedNumber {
  id: number;
  numbers: number[];
  score: number | null;
  rationale: Record<string, string>;
  memo: string;
  created_at: string;
}

// ───────── 실전 당첨 시뮬레이션 ─────────
export interface RealSimDetail {
  round: number;
  rank: number;
  game: number[];
  actual: number[];
  bonus: number;
  matched: number;
}

export interface RealSimResult {
  method: string;
  window: number;
  n_games: number;
  sample_every: number;
  tested_rounds: number;
  total_games: number;
  total_spent: number;
  total_prize: number;
  net: number;
  roi: number;
  rank_counts: Record<string, number>;
  rank_rate: Record<string, number>;
  random_counts: Record<string, number>;
  random_rate: Record<string, number>;
  random_prize: number;
  random_net: number;
  random_roi: number;
  detail: RealSimDetail[];
}
