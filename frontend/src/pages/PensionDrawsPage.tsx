import { useEffect, useState } from 'react';
import { fetchPensionDraws } from '../api/lottery';
import type { PensionDraw } from '../types';
import './PensionDrawsPage.css';

export default function PensionDrawsPage() {
  const [draws, setDraws] = useState<PensionDraw[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 50;

  useEffect(() => {
    setLoading(true);
    fetchPensionDraws()
      .then(res => {
        const sorted = [...res.draws].reverse();
        setDraws(sorted);
        setTotal(res.total);
      })
      .finally(() => setLoading(false));
  }, []);

  const totalPages = Math.ceil(draws.length / PAGE_SIZE);
  const pageDraws = draws.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  return (
    <div className="pension-draws-page">
      <h1 className="page-title">연금복권 당첨 번호</h1>
      <div className="draws-meta">총 {total}회차</div>

      {loading ? (
        <div className="page-loading">불러오는 중...</div>
      ) : (
        <>
          <div className="pension-draws-table">
            <div className="pension-draws-header">
              <span>회차</span>
              <span>추첨일</span>
              <span>조</span>
              <span>당첨번호</span>
              <span>보너스번호</span>
            </div>
            {pageDraws.map(d => (
              <div className="pension-draws-row" key={d.round}>
                <span className="draws-round">{d.round}회</span>
                <span className="draws-date">{d.draw_date}</span>
                <span className="draws-grp">{d.grp}조</span>
                <span className="draws-num">{String(d.num).padStart(6, '0')}</span>
                <span className="draws-bonus">{String(d.bonus_num).padStart(6, '0')}</span>
              </div>
            ))}
          </div>

          {totalPages > 1 && (
            <div className="pagination">
              <button disabled={page === 1} onClick={() => setPage(p => p - 1)}>이전</button>
              <span>{page} / {totalPages}</span>
              <button disabled={page === totalPages} onClick={() => setPage(p => p + 1)}>다음</button>
            </div>
          )}
        </>
      )}
    </div>
  );
}
