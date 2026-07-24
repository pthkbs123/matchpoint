import { useEffect, useState } from 'react';

const API_BASE = 'http://localhost:8000';

function AnalyzingPage({ onNavigate, capturedBlob, onAnalysisComplete }) {
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!capturedBlob) {
      onNavigate('camera');
      return;
    }

    let cancelled = false;
    const formData = new FormData();
    formData.append('file', capturedBlob, 'capture.jpg');

    fetch(`${API_BASE}/analyze`, { method: 'POST', body: formData })
      .then((res) => {
        if (!res.ok) throw new Error('분석 요청이 실패했어요.');
        return res.json();
      })
      .then((data) => {
        if (cancelled) return;
        onAnalysisComplete(data);
        onNavigate('result');
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || '분석 중 오류가 발생했어요.');
      });

    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [capturedBlob]);

  if (error) {
    return (
      <section className="phone center-page">
        <p className="eyebrow">AI ANALYSIS</p>
        <h1>분석에 실패했어요</h1>
        <p className="subtext">
          {error}
          <br />
          백엔드 서버(localhost:8000)가 켜져 있는지 확인해주세요.
        </p>
        <button className="action primary" style={{ marginTop: 24, padding: '14px 22px' }} onClick={() => onNavigate('camera')}>
          다시 촬영하기
        </button>
      </section>
    );
  }

  return (
    <section className="phone center-page">
      <div className="loader" />
      <p className="eyebrow">AI ANALYSIS</p>
      <h1>구강 상태를 분석하고 있어요</h1>
      <p className="subtext">
        치아 영역과 잇몸 색상을 확인 중입니다.
        <br />
        잠시만 기다려 주세요.
      </p>
      <div className="progress">
        <span />
      </div>
    </section>
  );
}
export default AnalyzingPage;
