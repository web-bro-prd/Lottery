import { useState, useRef } from 'react';
import { collectPensionAll, collectPensionLatest, uploadPensionXlsx } from '../api/lottery';
import './PensionCollectPage.css';

export default function PensionCollectPage() {
  const [message, setMessage] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleCollectLatest = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await collectPensionLatest();
      setMessage(`[최신 수집] ${res.message}`);
    } catch (e) {
      setMessage(`오류: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const handleCollectAll = async () => {
    setLoading(true);
    setMessage(null);
    try {
      const res = await collectPensionAll();
      setMessage(`[전체 수집] ${res.saved}회차 저장 완료`);
    } catch (e) {
      setMessage(`오류: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) { setMessage('파일을 선택해주세요.'); return; }
    setLoading(true);
    setMessage(null);
    try {
      const res = await uploadPensionXlsx(file);
      setMessage(`[XLSX 업로드] 성공 ${res.success}회 / 실패 ${res.fail}회`);
    } catch (e) {
      setMessage(`오류: ${e}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="pension-collect-page">
      <h1 className="page-title">연금복권 데이터 수집</h1>

      <div className="collect-cards">
        <div className="collect-card">
          <h2>최신 데이터 수집</h2>
          <p>동행복권 API에서 신규 회차만 수집합니다.</p>
          <button className="btn-collect" onClick={handleCollectLatest} disabled={loading}>
            {loading ? '수집 중...' : '최신 수집'}
          </button>
        </div>

        <div className="collect-card">
          <h2>전체 데이터 수집</h2>
          <p>동행복권 API에서 전체 회차(1회~현재)를 수집합니다.</p>
          <button className="btn-collect btn-all" onClick={handleCollectAll} disabled={loading}>
            {loading ? '수집 중...' : '전체 수집'}
          </button>
        </div>

        <div className="collect-card">
          <h2>XLSX 파일 업로드</h2>
          <p>엑셀 파일로 데이터를 업로드합니다. (컬럼: No, 회차, 조, 당첨번호)</p>
          <input ref={fileRef} type="file" accept=".xlsx,.xls" className="file-input" />
          <button className="btn-collect btn-upload" onClick={handleUpload} disabled={loading}>
            {loading ? '업로드 중...' : '업로드'}
          </button>
        </div>
      </div>

      {message && (
        <div className={`collect-message ${message.startsWith('오류') ? 'error' : 'success'}`}>
          {message}
        </div>
      )}
    </div>
  );
}
