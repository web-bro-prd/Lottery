# 로또 분석 시스템

동행복권 API 기반 로또 번호 통계 분석 및 추천 시스템

## 프로젝트 구조

```
Lottery/
├── backend/                    # FastAPI 백엔드 (port 8010)
│   ├── main.py                 # FastAPI 앱 + 전체 API 엔드포인트
│   ├── config.py               # 환경변수 설정
│   ├── database.py             # SQLite CRUD
│   ├── collector.py            # 동행복권 API 크롤러
│   ├── requirements.txt
│   ├── .env.example
│   ├── analysis/
│   │   ├── stats.py            # 통계 분석 엔진
│   │   └── simulation.py       # 시뮬레이션 엔진
│   └── recommender/
│       └── engine.py           # 번호 추천 엔진
└── frontend/                   # React + TypeScript (port 3010)
    └── src/
        ├── pages/              # 각 페이지
        ├── components/         # 공통 컴포넌트
        ├── api/                # API 클라이언트
        └── types/              # TypeScript 타입
```

## 시작하기

### 1. 백엔드

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
python main.py
```

### 2. 프론트엔드

```bash
cd frontend
npm install
npm run dev
```

### 3. 데이터 수집

서버 시작 후 브라우저에서 `데이터 수집` 메뉴 → "최신 회차 수집 시작" 클릭
또는 API 직접 호출:
```bash
curl -X POST http://localhost:8010/api/collect/latest
```

## 주요 기능

| 기능 | 설명 |
|------|------|
| 데이터 수집 | 동행복권 API 자동 수집 + CSV 업로드 |
| 당첨 번호 | 전체 회차 조회, 페이지네이션, 검색 |
| 통계 분석 | 번호 빈도, 홀/짝, 고/저, 구간, 합계 분포, 번호 조합 |
| 트렌드 분석 | 최근 N회 핫/콜드 번호 분석 |
| 시뮬레이션 | 랜덤 구매 ROI, 몬테카를로 |
| 번호 추천 | 빈도/트렌드/균형/랜덤 4가지 전략 |

## 기술 스택

- Backend: FastAPI + SQLite + Python
- Frontend: React 19 + TypeScript + Vite + Recharts
- Port: Backend 8010, Frontend 3010
