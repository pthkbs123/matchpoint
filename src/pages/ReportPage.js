import { useEffect, useMemo, useState } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
} from 'chart.js';
import { Line } from 'react-chartjs-2';
import { apiFetch } from '../api';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler);

const trendOptions = {
  responsive: true,
  maintainAspectRatio: false,
  interaction: { intersect: false, mode: 'index' },
  plugins: {
    legend: { display: false },
    tooltip: {
      displayColors: false,
      callbacks: { label: (context) => `구강 건강 점수: ${context.parsed.y}점` },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      border: { display: false },
      ticks: { color: '#8a94a6', font: { size: 10 }, maxTicksLimit: 7 },
    },
    y: {
      min: 0,
      max: 100,
      border: { display: false },
      grid: { color: '#edf1f6' },
      ticks: { stepSize: 20, color: '#8a94a6', font: { size: 10 } },
    },
  },
};

function scoreCopy(score) {
  if (score == null) return '첫 촬영을 기다리고 있어요.';
  if (score >= 80) return '현재 기록은 안정적인 범위예요.';
  if (score >= 50) return '조금 더 주의 깊게 관찰해 주세요.';
  return '변화가 커서 치과 상담을 권장해요.';
}

function ReportPage({ onNavigate, token, selectedChildId }) {
  const [summary, setSummary] = useState(null);
  const [range, setRange] = useState('weekly');
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    const query = selectedChildId ? `?child_id=${selectedChildId}` : '';
    setIsLoading(true);
    apiFetch(`/api/report/summary${query}`, { token })
      .then((data) => { if (!cancelled) setSummary(data); })
      .catch((err) => { if (!cancelled) setError(err.message); })
      .finally(() => { if (!cancelled) setIsLoading(false); });
    return () => { cancelled = true; };
  }, [token, selectedChildId]);

  const trend = range === 'weekly' ? summary?.weekly_trend : summary?.monthly_trend;
  const totalScans = summary?.total_scans ?? 0;
  const currentScore = summary?.current_score;
  const scoreChange = summary?.score_change;
  const hasTrend = totalScans >= 3 && trend?.scores?.length >= 3;

  const data = useMemo(() => ({
    labels: trend?.labels || [],
    datasets: [{
      label: '구강 건강 점수',
      data: trend?.scores || [],
      borderColor: '#2f80ed',
      backgroundColor: 'rgba(47, 128, 237, 0.12)',
      pointBackgroundColor: '#ffffff',
      pointBorderColor: '#2f80ed',
      pointBorderWidth: 2,
      pointRadius: 4,
      borderWidth: 3,
      tension: 0.35,
      fill: true,
    }],
  }), [trend]);

  const changeLabel = scoreChange == null
    ? '비교할 이전 기록이 없어요'
    : scoreChange === 0
      ? '이전 촬영과 동일해요'
      : `이전 촬영보다 ${Math.abs(scoreChange)}점 ${scoreChange > 0 ? '올랐어요' : '내렸어요'}`;

  return (
    <section className="phone">
      <header className="report-header">
        <button className="back-button" onClick={() => onNavigate('home')}>← 뒤로</button>
        <p className="eyebrow" style={{ color: '#cfe3ff' }}>HEALTH REPORT</p>
        <h1>구강 건강 리포트</h1>
        <p>{scoreCopy(currentScore)}</p>
      </header>

      <div className="report-body">
        <div className="report-score-grid">
          <article><small>최근 점수</small><strong>{totalScans ? currentScore : '--'}</strong><span>점</span></article>
          <article><small>최근 평균</small><strong>{summary?.monthly_average ?? '--'}</strong><span>점</span></article>
          <article><small>누적 촬영</small><strong>{totalScans}</strong><span>회</span></article>
        </div>

        {summary?.attention_required && (
          <div className="attention-banner"><span>!</span><div><strong>점수 하락이 감지됐어요</strong><p>같은 환경에서 다시 촬영하고 변화가 계속되면 치과 상담을 권장해요.</p></div></div>
        )}

        <div className="period">
          <div><h2>변화 추이</h2><p>{changeLabel}</p></div>
          <div className="range-tabs" aria-label="리포트 기간">
            <button className={range === 'weekly' ? 'active' : ''} onClick={() => setRange('weekly')}>최근 7회</button>
            <button className={range === 'monthly' ? 'active' : ''} onClick={() => setRange('monthly')}>최근 30회</button>
          </div>
        </div>

        <article className="trend-card report-trend-card">
          {isLoading ? (
            <p className="page-state">리포트를 불러오는 중이에요...</p>
          ) : error ? (
            <p className="social-error" role="alert">{error}</p>
          ) : hasTrend ? (
            <div className="trend-line large"><Line data={data} options={trendOptions} /></div>
          ) : (
            <div className="report-onboarding">
              <span>▥</span>
              <h3>추이 분석까지 {Math.max(3 - totalScans, 0)}회 남았어요</h3>
              <p>조명과 촬영 위치를 비슷하게 유지해 3회 이상 기록하면 변화 그래프를 확인할 수 있어요.</p>
              <button className="login-button" onClick={() => onNavigate('camera')}>촬영하기</button>
            </div>
          )}
        </article>

        <article className="weekly-report-card">
          <div className="card-head"><h3>이번 주 관리 요약</h3><span>{totalScans}회 기록</span></div>
          <div className="weekly-summary-row">
            <div><span>기록 습관</span><strong>{summary?.streak_days ?? 0}일 연속</strong></div>
            <div><span>최근 변화</span><strong className={scoreChange < 0 ? 'down' : ''}>{scoreChange == null ? '--' : `${scoreChange > 0 ? '+' : ''}${scoreChange}점`}</strong></div>
          </div>
          <p>매주 같은 요일과 시간대에 촬영하면 조명 차이를 줄여 비교하기 좋아요.</p>
        </article>

        <p className="medical-disclaimer">이 결과는 촬영 상태와 AI 분석에 따른 참고 지표이며 의료진의 진단을 대신하지 않습니다.</p>
      </div>

      <nav className="bottom-nav">
        <button className="nav-item" onClick={() => onNavigate('home')}><span>⌂</span>홈</button>
        <button className="nav-item active"><span>▥</span>리포트</button>
        <button className="nav-item" onClick={() => onNavigate('camera')}><span>◎</span>촬영</button>
      </nav>
    </section>
  );
}

export default ReportPage;
