function ResultPage({ onNavigate, analysisResult, capturedUrl }) {
  const cavityCount = analysisResult?.summary?.cavity_count ?? 0;
  const normalCount = analysisResult?.summary?.normal_count ?? 0;
  const hasCavity = cavityCount > 0;
  const imageSize = analysisResult?.image_size;

  return (
    <section className="phone">
      <div className="page-content">
        <div className="top-row">
          <button className="back-button" onClick={() => onNavigate('home')}>← 홈</button>
          <button className="text-button" onClick={() => onNavigate('report')}>리포트 보기</button>
        </div>

        <div className="result-hero">
          <span className="check">{hasCavity ? '!' : '✓'}</span>
          <h1>{hasCavity ? '충치 의심 부위가 발견됐어요' : '분석이 완료됐어요'}</h1>
          <p className="subtext">
            {hasCavity
              ? `충치로 의심되는 부위 ${cavityCount}곳이 감지됐어요. 치과 상담을 권장드려요.`
              : '전체적으로 양호한 상태입니다.'}
          </p>
        </div>

        {capturedUrl && imageSize && (
          <div className="result-image">
            <img src={capturedUrl} alt="분석된 사진" />
            {analysisResult.detections.map((d, i) => {
              const left = (d.box.x1 / imageSize.width) * 100;
              const top = (d.box.y1 / imageSize.height) * 100;
              const boxW = ((d.box.x2 - d.box.x1) / imageSize.width) * 100;
              const boxH = ((d.box.y2 - d.box.y1) / imageSize.height) * 100;
              return (
                <span
                  key={i}
                  className={`detect-box ${d.class === 'cavity' ? 'cavity' : 'normal'}`}
                  style={{ left: `${left}%`, top: `${top}%`, width: `${boxW}%`, height: `${boxH}%` }}
                  title={`${d.class} ${(d.confidence * 100).toFixed(0)}%`}
                />
              );
            })}
          </div>
        )}

        <div className="metric-grid">
          <article className={`metric ${hasCavity ? 'watch' : 'good'}`}>
            <span>충치 의심</span>
            <strong>{cavityCount}</strong>
            <span>개 부위</span>
          </article>
          <article className="metric good">
            <span>정상 치아</span>
            <strong>{normalCount}</strong>
            <span>개 부위</span>
          </article>
        </div>

        <div className="notice">
          <strong>{hasCavity ? '치과 상담을 권장해요' : '좋은 상태를 유지하고 있어요'}</strong>
          <br />
          {hasCavity
            ? '충치 의심 부위가 발견됐어요. 정확한 진단은 치과에서 받아보세요.'
            : '꾸준한 관리로 건강한 치아 상태를 유지해 주세요.'}
        </div>
      </div>
      <nav className="bottom-nav">
        <button className="nav-item" onClick={() => onNavigate('camera')}><span>←</span>재촬영</button>
        <button className="nav-item active"><span>◉</span>결과</button>
        <button className="nav-item" onClick={() => onNavigate('home')}><span>⌂</span>홈</button>
      </nav>
    </section>
  );
}
export default ResultPage;
