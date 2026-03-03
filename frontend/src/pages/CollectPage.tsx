import { useState, useRef } from 'react';
import { collectLatest, collectSingle, uploadCsv, uploadXlsx } from '../api/lottery';
import './CollectPage.css';

export default function CollectPage() {
  const [msg, setMsg] = useState('');
  const [loading, setLoading] = useState(false);
  const [singleRound, setSingleRound] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);
  const xlsxRef = useRef<HTMLInputElement>(null);

  const handleCollectLatest = async () => {
    setLoading(true);
    setMsg('');
    try {
      const r = await collectLatest();
      setMsg(`수집 시작! DB 최신 회차: ${r.db_latest_round}회 — ${r.message}`);
    } catch {
      setMsg('수집 요청 실패');
    } finally {
      setLoading(false);
    }
  };

  const handleCollectSingle = async () => {
    if (!singleRound) return;
    setLoading(true);
    setMsg('');
    try {
      const r = await collectSingle(Number(singleRound));
      setMsg(`${r.data.round}회 (${r.data.draw_date}) 수집 완료!`);
    } catch {
      setMsg('해당 회차 데이터를 가져올 수 없습니다.');
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) return;
    setLoading(true);
    setMsg('');
    try {
      const r = await uploadCsv(file);
      setMsg(`업로드 완료! 성공: ${r.success}개, 실패: ${r.fail}개`);
    } catch {
      setMsg('CSV 업로드 실패');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadXlsx = async () => {
    const file = xlsxRef.current?.files?.[0];
    if (!file) return;
    setLoading(true);
    setMsg('');
    try {
      const r = await uploadXlsx(file);
      setMsg(`엑셀 업로드 완료! 성공: ${r.success}개, 실패: ${r.fail}개 (${r.filename})`);
    } catch {
      setMsg('엑셀 업로드 실패');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="collect-page">
      <h1 className="page-title">데이터 수집</h1>

      {msg && <div className={`alert ${msg.includes('실패') ? 'alert-error' : 'alert-success'}`}>{msg}</div>}

      {/* 최신 회차 자동 수집 */}
      <section className="section">
        <h2 className="section-title">최신 회차 자동 수집</h2>
        <p className="section-desc">
          동행복권 API에서 DB에 없는 최신 회차까지 자동으로 수집합니다.
          처음 실행 시 전체 회차(1회~최신회)를 수집하므로 시간이 다소 걸립니다.
        </p>
        <button className="btn-primary" onClick={handleCollectLatest} disabled={loading}>
          {loading ? '수집 중...' : '최신 회차 수집 시작'}
        </button>
      </section>

      {/* 단일 회차 수집 */}
      <section className="section">
        <h2 className="section-title">특정 회차 수집</h2>
        <div className="input-row">
          <input
            type="number"
            placeholder="회차 번호 (예: 1148)"
            value={singleRound}
            onChange={e => setSingleRound(e.target.value)}
          />
          <button className="btn-secondary" onClick={handleCollectSingle} disabled={loading || !singleRound}>
            수집
          </button>
        </div>
      </section>

      {/* 동행복권 공식 엑셀 업로드 */}
      <section className="section">
        <h2 className="section-title">동행복권 공식 엑셀 업로드 (.xlsx)</h2>
        <p className="section-desc">
          동행복권 홈페이지에서 다운로드한 <strong>로또 회차별 당첨번호.xlsx</strong> 파일을 업로드합니다.
          1회~최신회차까지 한 번에 등록 가능합니다.
        </p>
        <div className="input-row">
          <input type="file" accept=".xlsx" ref={xlsxRef} />
          <button className="btn-primary" onClick={handleUploadXlsx} disabled={loading}>
            {loading ? '업로드 중...' : '엑셀 업로드'}
          </button>
        </div>
      </section>

      {/* CSV 업로드 */}
      <section className="section">
        <h2 className="section-title">CSV 파일 업로드</h2>
        <p className="section-desc">
          CSV 파일의 예상 컬럼: <code>회차, 추첨일, 번호1, 번호2, 번호3, 번호4, 번호5, 번호6, 보너스</code>
        </p>
        <div className="input-row">
          <input type="file" accept=".csv" ref={fileRef} />
          <button className="btn-secondary" onClick={handleUpload} disabled={loading}>
            업로드
          </button>
        </div>
      </section>

      {/* 안내 */}
      <section className="section info-section">
        <h2 className="section-title">안내사항</h2>
        <ul className="info-list">
          <li>동행복권 API는 1회~현재 회차의 당첨 번호를 제공합니다.</li>
          <li>최초 전체 수집 시 약 5~10분 소요될 수 있습니다.</li>
          <li>수집은 백그라운드에서 진행되므로 페이지 이동이 가능합니다.</li>
          <li><strong>엑셀 업로드 권장</strong>: 동행복권 공식 엑셀 파일로 1회~최신회를 즉시 등록할 수 있습니다.</li>
          <li>엑셀 업로드 후 날짜가 없는 회차는 "최신 회차 자동 수집"으로 보완하세요.</li>
          <li>엑셀/CSV 업로드와 API 수집을 혼용할 수 있습니다 (중복 데이터는 자동 덮어쓰기).</li>
        </ul>
      </section>
    </div>
  );
}
