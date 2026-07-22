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

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler
);

function MainPage({ onNavigate }) {
  const weeklyScoreData = {
    labels: ['월', '화', '수', '목', '금', '토', '일'],
    datasets: [
      {
        label: '구강 건강 점수',
        data: [72, 75, 74, 78, 80, 79, 84],
        borderColor: '#2f80ed',
        backgroundColor: 'rgba(47, 128, 237, 0.12)',
        pointBackgroundColor: '#ffffff',
        pointBorderColor: '#2f80ed',
        pointBorderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 3,
        tension: 0.38,
        fill: true,
      },
    ],
  };

  const weeklyScoreOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: {
        displayColors: false,
        callbacks: {
          label: (context) => `${context.parsed.y}점`,
        },
      },
    },
    scales: {
      x: {
        grid: { display: false },
        border: { display: false },
        ticks: { color: '#8a94a6', font: { size: 10 } },
      },
      y: {
        display: false,
        min: 60,
        max: 100,
      },
    },
  };

  return (
    <section className="phone">
      <div className="page-content">
        <div className="top-row">
          <div><p className="eyebrow">SMILEGUARD</p><h1>안녕하세요, 한이음 님</h1><p className="subtext">오늘도 건강한 미소를 확인해 보세요.</p></div>
          <button
            className="profile-button"
            onClick={() => onNavigate('mypage')}
            aria-label="마이페이지로 이동"
          >
            <img src="/profile-avatar.svg" alt="한이음 님 프로필" />
          </button>
        </div>
        <div className="start-card">
          <button className="camera-start" onClick={() => onNavigate('camera')} aria-label="촬영 시작">⌁</button>
          <h2>구강 촬영 시작</h2><p>오늘은 아직 촬영하지 않았어요</p>
        </div>
        <div className="report-card">
          <div className="card-head"><h2>7월 리포트</h2><button className="text-button" onClick={() => onNavigate('report')}>전체보기 ›</button></div>
          <div className="mini-chart">
            <Line data={weeklyScoreData} options={weeklyScoreOptions} />
          </div>
          <div className="score-row"><div className="score"><strong>84</strong><span> 점 · 양호</span></div><span className="change">지난주 대비 +5</span></div>
        </div>
      </div>
      <nav className="bottom-nav"><button className="nav-item active"><span>◉</span>점수</button><button className="nav-item" onClick={() => onNavigate('report')}><span>▧</span>사진</button><button className="nav-item" onClick={() => onNavigate('mypage')}><span>⚙</span>설정</button></nav>
    </section>
  );
}
export default MainPage;
