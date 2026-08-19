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

const chartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { display: false },
    tooltip: {
      displayColors: false,
      callbacks: { label: (context) => `${context.parsed.y}점` },
    },
  },
  scales: {
    x: {
      grid: { display: false },
      border: { display: false },
      ticks: { color: '#8a94a6', font: { size: 10 } },
    },
    y: { display: false, min: 0, max: 100 },
  },
};

function MainPage({ onNavigate, user, token, selectedChildId, onSelectChild }) {
  const userName = user?.name || user?.nickname || '보호자';
  const profileImage = user?.picture || user?.profileImage || '/profile-avatar.svg';
  const [summary, setSummary] = useState(null);
  const [children, setChildren] = useState([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;

    apiFetch('/api/children', { token })
      .then((data) => {
        if (cancelled) return;
        const list = data.children || [];
        setChildren(list);
        if (list.length > 0 && !list.some((child) => child.id === selectedChildId)) {
          onSelectChild(list[0].id);
        }
      })
      .finally(() => { if (!cancelled) setIsLoading(false); });

    return () => { cancelled = true; };
  }, [token, selectedChildId, onSelectChild]);

  useEffect(() => {
    if (!token) return undefined;
    let cancelled = false;
    const query = selectedChildId ? `?child_id=${selectedChildId}` : '';
    apiFetch(`/api/report/summary${query}`, { token })
      .then((data) => { if (!cancelled) setSummary(data); })
      .catch(() => { if (!cancelled) setSummary(null); });
    return () => { cancelled = true; };
  }, [token, selectedChildId]);

  const selectedChild = children.find((child) => child.id === selectedChildId);
  const trend = summary?.weekly_trend;
  const totalScans = summary?.total_scans ?? 0;
  const hasTrend = totalScans >= 3 && trend?.scores?.length >= 3;
  const currentScore = summary?.current_score;

  const chartData = useMemo(() => ({
    labels: trend?.labels || [],
    datasets: [{
      label: '구강 건강 점수',
      data: trend?.scores || [],
      borderColor: '#2f80ed',
      backgroundColor: 'rgba(47, 128, 237, 0.12)',
      pointBackgroundColor: '#ffffff',
      pointBorderColor: '#2f80ed',
      pointBorderWidth: 2,
      pointRadius: 3,
      borderWidth: 3,
      tension: 0.38,
      fill: true,
    }],
  }), [trend]);

  return (
    <section className="phone">
      <div className="page-content">
        <div className="top-row">
          <div>
            <p className="eyebrow">SMILEGUARD</p>
            <h1>안녕하세요, {userName} 님</h1>
            <p className="subtext">아이의 구강 변화를 꾸준히 기록해 보세요.</p>
          </div>
          <button className="profile-button" onClick={() => onNavigate('mypage')} aria-label="마이페이지로 이동">
            <img src={profileImage} alt={`${userName} 님 프로필`} />
          </button>
        </div>

        <button className="active-child-card" onClick={() => onNavigate('child-profile')}>
          <span className="child-avatar">{selectedChild?.name?.slice(0, 1) || '+'}</span>
          <span>
            <small>현재 관리 중</small>
            <strong>{isLoading ? '자녀 정보를 불러오는 중' : selectedChild?.name || '자녀를 먼저 등록해 주세요'}</strong>
          </span>
          <b>변경 ›</b>
        </button>

        <div className="start-card">
          <button
            className="camera-start"
            onClick={() => selectedChild ? onNavigate('camera') : onNavigate('child-profile')}
            aria-label="촬영 시작"
          >
            ◎
          </button>
          <h2>{selectedChild ? `${selectedChild.name} 구강 촬영` : '자녀 프로필을 등록해 주세요'}</h2>
          <p>{selectedChild ? '위생 커버를 교체한 뒤 촬영을 시작해 주세요.' : '촬영 기록을 자녀별로 안전하게 관리할 수 있어요.'}</p>
        </div>

        <div className="report-card">
          <div className="card-head">
            <h2>구강 건강 추이</h2>
            <button className="text-button" onClick={() => onNavigate('report')}>리포트 보기 ›</button>
          </div>
          <div className="mini-chart">
            {hasTrend ? (
              <Line data={chartData} options={chartOptions} />
            ) : (
              <div className="trend-empty">
                <strong>{Math.min(totalScans, 3)} / 3회</strong>
                <span>3회 이상 촬영하면 변화 그래프가 열려요.</span>
                <div><i style={{ width: `${Math.min(totalScans / 3, 1) * 100}%` }} /></div>
              </div>
            )}
          </div>
          <div className="score-row">
            <div className="score">
              <strong>{currentScore ?? '--'}</strong>
              <span>{currentScore == null ? ' 첫 촬영 전' : ` 점 · ${currentScore >= 80 ? '양호' : currentScore >= 50 ? '주의' : '관리 필요'}`}</span>
            </div>
            <span className="change">누적 측정 {totalScans}회</span>
          </div>
        </div>

        <button className="care-tip" onClick={() => onNavigate('care-guide')}>
          <span>✦</span>
          <span><strong>촬영 전 위생·품질 체크</strong><small>커버 교체와 선명한 촬영 방법을 확인해요.</small></span>
          <b>›</b>
        </button>
      </div>
      <nav className="bottom-nav">
        <button className="nav-item active"><span>⌂</span>홈</button>
        <button className="nav-item" onClick={() => onNavigate('report')}><span>▥</span>리포트</button>
        <button className="nav-item" onClick={() => onNavigate('mypage')}><span>●</span>관리</button>
      </nav>
    </section>
  );
}

export default MainPage;
