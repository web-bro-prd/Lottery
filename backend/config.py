from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # 서버 설정
    HOST: str = "0.0.0.0"
    PORT: int = 8010
    CORS_ORIGINS: str = "http://localhost:3010,http://localhost:5173"

    # DB
    DB_PATH: str = "data/lottery.db"

    # 동행복권 API
    LOTTO_API_URL: str = "https://www.dhlottery.co.kr/common.do"

    # 데이터 수집 설정
    COLLECT_START_ROUND: int = 1       # 수집 시작 회차
    COLLECT_BATCH_SIZE: int = 50       # 한 번에 수집할 회차 수
    COLLECT_DELAY_SEC: float = 0.3     # 요청 간 딜레이 (초)

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
