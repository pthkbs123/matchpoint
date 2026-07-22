import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
} from 'chart.js';
import { Line } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip
);

function ReportPage({ onNavigate }) {
  const labels = ['7/1', '7/5', '7/9', '7/13', '7/17', '7/21', '7/25'];

  const createTrendData = (label, values, color) => ({
    labels,
    datasets: [
      {
        label,
        data: values,
        borderColor: color,
        backgroundColor: color,
        pointBackgroundColor: '#ffffff',
        pointBorderColor: color,
        pointBorderWidth: 2,
        pointRadius: 3,
        pointHoverRadius: 5,
        borderWidth: 3,
        tension: 0.38,
      },
    ],
  });

  const trendOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { intersect: false, mode: 'index' },
    plugins: {
      legend: { display: false },
      tooltip: {
        displayColors: false,
        callbacks: {
          label: (context) => `${context.dataset.label}: ${context.parsed.y}`,
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
        beginAtZero: true,
        suggestedMax: 60,
        border: { display: false },
        grid: { color: '#edf1f6' },
        ticks: { stepSize: 20, color: '#8a94a6', font: { size: 10 } },
      },
    },
  };

  const yellowingData = createTrendData(
    '황변 지수',
    [31, 29, 30, 27, 26, 25, 24],
    '#2f80ed'
  );
  const gumData = createTrendData(
    '잇몸 염증 지수',
    [30, 31, 29, 33, 34, 36, 38],
    '#f39a3d'
  );

  return (
    <section className="phone">
      <header className="report-header">
        <button className="back-button" onClick={() => onNavigate('home')}>← 뒤로가기</button>
        <p className="eyebrow" style={{ color: '#cfe3ff' }}>MONTHLY REPORT</p>
        <h1>7월 구강 건강 리포트</h1>
        <p>꾸준히 좋아지고 있어요. 현재 점수는 84점입니다.</p>
      </header>
      <div className="report-body">
        <div className="period">
          <h2>최근 변화</h2>
          <button className="text-button">2026년 7월⌄</button>
        </div>
        <article className="trend-card">
          <h3>치아 황변 지수</h3>
          <p>낮을수록 깨끗한 상태예요 · 현재 24</p>
          <div className="trend-line">
            <Line data={yellowingData} options={trendOptions} />
          </div>
        </article>
        <article className="trend-card">
          <h3>잇몸 염증 지수</h3>
          <p>지난달 대비 3점 증가 · 현재 38</p>
          <div className="trend-line">
            <Line data={gumData} options={trendOptions} />
          </div>
        </article>
      </div>
      <nav className="bottom-nav">
        <button className="nav-item" onClick={() => onNavigate('home')}><span>⌂</span>홈</button>
        <button className="nav-item active"><span>▥</span>리포트</button>
        <button className="nav-item" onClick={() => onNavigate('camera')}><span>◉</span>촬영</button>
      </nav>
    </section>
  );
}
export default ReportPage;
