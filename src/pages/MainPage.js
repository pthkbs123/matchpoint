function MainPage({ onNavigate }) {
  return (
    <section className="phone">
      <div className="page-content">
        <div className="top-row">
          <div><p className="eyebrow">SMILEGUARD</p><h1>안녕하세요, 한이음 님</h1><p className="subtext">오늘도 건강한 미소를 확인해 보세요.</p></div>
          <button className="icon-button" aria-label="알림">♧</button>
        </div>
        <div className="start-card">
          <button className="camera-start" onClick={() => onNavigate('camera')} aria-label="촬영 시작">⌁</button>
          <h2>구강 촬영 시작</h2><p>오늘은 아직 촬영하지 않았어요</p>
        </div>
        <div className="report-card">
          <div className="card-head"><h2>7월 리포트</h2><button className="text-button" onClick={() => onNavigate('report')}>전체보기 ›</button></div>
          <div className="mini-chart">{[42,52,48,65,62,74,82].map((h,i)=><i key={i} className={`bar ${i===6?'active':''}`} style={{'--h':`${h}%`}} />)}</div>
          <div className="score-row"><div className="score"><strong>84</strong><span> 점 · 양호</span></div><span className="change">지난주 대비 +5</span></div>
        </div>
      </div>
      <nav className="bottom-nav"><button className="nav-item active"><span>◉</span>점수</button><button className="nav-item" onClick={() => onNavigate('report')}><span>▧</span>사진</button><button className="nav-item"><span>⚙</span>설정</button></nav>
    </section>
  );
}
export default MainPage;
