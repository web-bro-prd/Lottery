import { useEffect, useState } from 'react';
import { fetchDraws } from '../api/lottery';
import type { DrawResult } from '../types';
import LottoBall from '../components/LottoBall';
import './DrawsPage.css';

export default function DrawsPage() {
  const [draws, setDraws] = useState<DrawResult[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const PER_PAGE = 30;

  useEffect(() => {
    fetchDraws()
      .then(r => setDraws(r.draws.slice().reverse()))
      .finally(() => setLoading(false));
  }, []);

  const filtered = search
    ? draws.filter(d => String(d.round).includes(search))
    : draws;

  const total = Math.ceil(filtered.length / PER_PAGE);
  const paged = filtered.slice((page - 1) * PER_PAGE, page * PER_PAGE);

  return (
    <div className="draws-page">
      <h1 className="page-title">당첨 번호</h1>

      <div className="search-row">
        <input
          type="text"
          placeholder="회차 검색..."
          value={search}
          onChange={e => { setSearch(e.target.value); setPage(1); }}
        />
        <span className="total-info">총 {filtered.length}회차</span>
      </div>

      {loading ? (
        <div className="page-loading">불러오는 중...</div>
      ) : (
        <>
          <section className="section">
            <table className="draws-table">
              <thead>
                <tr>
                  <th>회차</th>
                  <th>추첨일</th>
                  <th>당첨 번호</th>
                  <th>보너스</th>
                  <th>1등 당첨자</th>
                  <th>1등 당첨금</th>
                </tr>
              </thead>
              <tbody>
                {paged.map(draw => (
                  <tr key={draw.round}>
                    <td className="round-cell">{draw.round}회</td>
                    <td>{draw.draw_date}</td>
                    <td>
                      <div className="balls-cell">
                        {[draw.num1, draw.num2, draw.num3, draw.num4, draw.num5, draw.num6].map(n => (
                          <LottoBall key={n} number={n} size="sm" />
                        ))}
                      </div>
                    </td>
                    <td><LottoBall number={draw.bonus} bonus size="sm" /></td>
                    <td>{draw.win1_count != null ? `${draw.win1_count}명` : '-'}</td>
                    <td className="prize-cell">
                      {draw.win1_prize != null
                        ? `${Math.round(draw.win1_prize / 100_000_000).toLocaleString()}억`
                        : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          <div className="pagination">
            <button onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>이전</button>
            <span>{page} / {total}</span>
            <button onClick={() => setPage(p => Math.min(total, p + 1))} disabled={page === total}>다음</button>
          </div>
        </>
      )}
    </div>
  );
}
