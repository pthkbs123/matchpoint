import { useEffect, useMemo, useState } from 'react';
import { apiFetch } from '../api';
import {
  PREPROCESS_LABELS,
  REFERENCE_LABELS,
  colorTestsToCsv,
  createColorTestRecord,
  loadColorTestRecords,
  recommendColorCalibration,
  saveColorTestRecords,
  summarizeColorTests,
} from '../colorTestResults';

const CONDITION_LABELS = {
  same: '같은 조명·각도',
  bright: '밝은 조명',
  dim: '어두운 조명',
  angle: '각도 변경',
};

function value(value, digits = 1) {
  return value == null || !Number.isFinite(Number(value)) ? '-' : Number(value).toFixed(digits);
}

const AGREEMENT_LABELS = { high: '높음', medium: '보통', low: '낮음' };

function ColorAnalysisTestPage({ onNavigate, onBack, token, selectedChildId }) {
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [condition, setCondition] = useState('same');
  const [reference, setReference] = useState('unknown');
  const [note, setNote] = useState('');
  const [records, setRecords] = useState(() => loadColorTestRecords());
  const [latest, setLatest] = useState(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState('');
  const [baseline, setBaseline] = useState(null);
  const [baselineMessage, setBaselineMessage] = useState('');
  const [isResetting, setIsResetting] = useState(false);

  useEffect(() => () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const summaries = useMemo(() => summarizeColorTests(records), [records]);
  const calibration = useMemo(() => recommendColorCalibration(records), [records]);

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    const query = selectedChildId == null ? '' : `?child_id=${selectedChildId}`;
    apiFetch(`/api/color-baseline/status${query}`, { token })
      .then((data) => { if (!cancelled) setBaseline(data.baseline); })
      .catch((err) => { if (!cancelled) setError(err.message); });
    return () => { cancelled = true; };
  }, [token, selectedChildId]);

  const handleFile = (event) => {
    const selected = event.target.files?.[0] || null;
    setFile(selected);
    setLatest(null);
    setError('');
    setPreviewUrl((current) => {
      if (current) URL.revokeObjectURL(current);
      return selected ? URL.createObjectURL(selected) : '';
    });
  };

  const runComparison = async () => {
    if (!file || isRunning) return;
    setIsRunning(true);
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      const response = await apiFetch('/api/color-analysis/compare', {
        token,
        method: 'POST',
        body: formData,
      });
      const record = createColorTestRecord(response, {
        fileName: file.name,
        condition,
        reference,
        note: note.trim(),
      });
      const next = [record, ...records];
      setLatest(record);
      setRecords(next);
      saveColorTestRecords(next);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsRunning(false);
    }
  };

  const clearRecords = () => {
    if (!window.confirm('이 브라우저에 저장된 색상 테스트 기록을 모두 지울까요?')) return;
    setRecords([]);
    setLatest(null);
    saveColorTestRecords([]);
  };

  const resetBaseline = async () => {
    if (isResetting) return;
    if (!window.confirm('기존 촬영 기록은 유지하고 개인 색상 기준만 새로 3회 수집할까요?')) return;
    setIsResetting(true);
    setError('');
    setBaselineMessage('');
    try {
      const response = await apiFetch('/api/color-baseline/reset', {
        token,
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ child_id: selectedChildId ?? null }),
      });
      setBaseline(response.baseline);
      setBaselineMessage(response.message);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsResetting(false);
    }
  };

  const downloadCsv = () => {
    const blob = new Blob([`\ufeff${colorTestsToCsv(records)}`], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = `smileguard-color-test-${new Date().toISOString().slice(0, 10)}.csv`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <section className="phone">
      <div className="mypage-content color-test-content">
        <div className="mypage-top">
          <button className="back-button" onClick={onBack || (() => onNavigate('mypage'))}>← 뒤로</button>
          <h1>색상 분석 테스트</h1>
          <span className="mypage-top-space" />
        </div>

        <div className="color-test-guide">
          <strong>실데이터 보정용</strong>
          <p>같은 치아를 조건별로 촬영해 전처리 3종의 점수 변동 폭을 비교합니다. 의료 진단값으로 사용하지 않습니다.</p>
        </div>

        <div className="color-baseline-control">
          <div>
            <strong>
              {baseline?.available === false
                ? '자녀를 먼저 선택해 주세요'
                : baseline?.ready ? '개인 3회 기준 사용 중' : '개인 기준 수집 중'}
            </strong>
            <small>
              {baseline?.available === false
                ? '개인 기준은 자녀별로 관리됩니다.'
                : baseline?.ready
                ? `기준 ${baseline.generation || 1}세대`
                : `${Math.min(baseline?.yellowing?.sample_count ?? 0, baseline?.gum_inflammation?.sample_count ?? 0)}/3회 완료`}
            </small>
          </div>
          <button type="button" disabled={isResetting || selectedChildId == null} onClick={resetBaseline}>
            {isResetting ? '재설정 중' : '기준 다시 만들기'}
          </button>
        </div>
        {baselineMessage && <p className="color-baseline-message">{baselineMessage}</p>}

        <label className="color-test-upload">
          {previewUrl ? <img src={previewUrl} alt="테스트할 치아" /> : <span>＋<b>치아 사진 선택</b><small>JPG 또는 PNG</small></span>}
          <input type="file" accept="image/*" onChange={handleFile} />
        </label>

        <div className="color-test-fields">
          <label>
            촬영 조건
            <select value={condition} onChange={(event) => setCondition(event.target.value)}>
              {Object.entries(CONDITION_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </label>
          <label>
            참고 상태
            <select value={reference} onChange={(event) => setReference(event.target.value)}>
              {Object.entries(REFERENCE_LABELS).map(([key, label]) => <option key={key} value={key}>{label}</option>)}
            </select>
          </label>
          <label className="wide">
            메모
            <input value={note} onChange={(event) => setNote(event.target.value)} placeholder="예: LED 2단계, 정면" />
          </label>
        </div>

        <button className="login-button" disabled={!file || isRunning} onClick={runComparison}>
          {isRunning ? '전처리 3종 분석 중...' : '전처리 3종 비교하기'}
        </button>
        {file && <small className="color-test-repeat-note">같은 사진으로 다시 누르면 반복 측정값도 별도 기록됩니다.</small>}
        {error && <p className="auth-error">{error}</p>}

        {latest && (
          <section className="color-test-section">
            <div className="card-head"><h2>방금 측정한 결과</h2><span>{CONDITION_LABELS[latest.condition]}</span></div>
            <div className="color-test-table-wrap">
              <table className="color-test-table">
                <thead><tr><th>전처리</th><th>황변</th><th>잇몸 LAB</th><th>HSV 보조</th><th>일치도</th><th>LAB b/a</th><th>HSV H/S/V</th></tr></thead>
                <tbody>
                  {latest.comparisons.map((item) => (
                    <tr key={item.mode}>
                      <th>{PREPROCESS_LABELS[item.mode] || item.mode}</th>
                      <td>{value(item.yellowingIndex)}</td>
                      <td>{value(item.gumInflammationIndex)}</td>
                      <td>{value(item.hsvHealthScore)}</td>
                      <td>{AGREEMENT_LABELS[item.labHsvAgreement] || '-'}</td>
                      <td>{value(item.meanLabB)} / {value(item.meanLabA)}</td>
                      <td>{value(item.meanHsvH)} / {value(item.meanHsvS)} / {value(item.meanHsvV)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        )}

        <section className="color-test-section">
          <div className="card-head"><h2>누적 안정성</h2><span>{records.length}회 측정</span></div>
          {records.length < 2 ? (
            <p className="color-test-empty">두 번 이상 측정하면 전처리별 점수 변동 폭을 확인할 수 있습니다.</p>
          ) : (
            <div className="color-test-summary-list">
              {summaries.map((item) => (
                <article key={item.mode}>
                  <strong>{PREPROCESS_LABELS[item.mode]}</strong>
                  <span>황변 범위 <b>{value(item.yellowing.range)}</b></span>
                  <span>잇몸 범위 <b>{value(item.gum.range)}</b></span>
                  <span>HSV 범위 <b>{value(item.hsvHealth.range)}</b></span>
                  <small>작을수록 촬영 조건 변화에 안정적</small>
                </article>
              ))}
            </div>
          )}
        </section>

        <section className="color-test-section">
          <div className="card-head"><h2>실데이터 보정 후보</h2><span>WB + CLAHE 기준</span></div>
          <p className="color-calibration-note">확인된 정상 사진 3장과 변화 사진 3장 이상이 필요합니다. 후보값은 검토 후 백엔드 설정에 적용합니다.</p>
          <div className="color-calibration-list">
            {[
              ['황변 LAB b', calibration.yellowLabB, 'COLOR_YELLOW_LAB_B'],
              ['잇몸 LAB a', calibration.gumLabA, 'COLOR_GUM_LAB_A'],
              ['잇몸 HSV S', calibration.gumHsvS, 'COLOR_GUM_HSV_S'],
            ].map(([label, item, envName]) => (
              <article key={label} className={item.ready ? 'ready' : 'waiting'}>
                <strong>{label}</strong>
                {item.ready ? (
                  <code>{envName}_GOOD={item.good}{'\n'}{envName}_HIGH={item.high}</code>
                ) : (
                  <span>정상 {item.normalCount}/3 · 변화 {item.affectedCount}/3</span>
                )}
              </article>
            ))}
          </div>
        </section>

        {records.length > 0 && (
          <section className="color-test-section">
            <div className="card-head"><h2>저장된 측정</h2><span>이 브라우저에 저장</span></div>
            <div className="color-test-history">
              {records.slice(0, 8).map((record) => (
                <div key={record.id}>
                  <strong>{record.fileName}</strong>
                  <span>{CONDITION_LABELS[record.condition] || record.condition} · {REFERENCE_LABELS[record.reference] || '기준 미확인'}</span>
                  <small>{new Date(record.createdAt).toLocaleString('ko-KR')}</small>
                </div>
              ))}
            </div>
            <div className="color-test-actions">
              <button type="button" onClick={downloadCsv}>CSV 내려받기</button>
              <button type="button" className="danger" onClick={clearRecords}>기록 지우기</button>
            </div>
          </section>
        )}
      </div>
    </section>
  );
}

export default ColorAnalysisTestPage;
