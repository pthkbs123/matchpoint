function ResultPage({ onNavigate, analysisResult, capturedUrl }) {
  const cavityCount = analysisResult?.summary?.cavity_count ?? 0;
  const normalCount = analysisResult?.summary?.normal_count ?? 0;
  const score = analysisResult?.summary?.score;
  const detections = analysisResult?.detections || [];
  const hasCavity = cavityCount > 0;
  const hasDetection = detections.length > 0;
  const imageSize = analysisResult?.image_size;

  return (
    <section className="phone">
      <div className="page-content">
        <div className="top-row">
          <button className="back-button" onClick={() => onNavigate('home')}>← 홈</button>
          <button className="text-button" onClick={() => onNavigate('report')}>리포트 보기</button>
        </div>

        <div className="result-hero">
          <span className={`check ${!hasDetection ? 'retry' : ''}`}>{!hasDetection ? '↻' : hasCavity ? '!' : '✓'}</span>
          <h1>{!hasDetection ? '치아 영역을 찾지 못했어요' : hasCavity ? '주의 깊게 볼 부위가 있어요' : '분석이 완료됐어요'}</h1>
          <p className="subtext">
            {!hasDetection
              ? '치아가 화면 중앙에 오도록 맞추고 조명을 확인한 뒤 다시 촬영해 주세요.'
              : hasCavity
              ? `AI가 주의가 필요한 부위 ${cavityCount}곳을 표시했어요. 같은 위치를 다시 확인해 주세요.`
              : '전체적으로 양호한 상태입니다.'}
          </p>
        </div>

        {capturedUrl && imageSize && (
          <div className="result-image">
            <img src={capturedUrl} alt="분석된 사진" />
            {detections.map((d, i) => {
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

        {hasDetection && <div className="metric-grid">
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
          {score != null && (
            <article className={`metric ${score >= 80 ? 'good' : 'watch'}`}>
              <span>이번 촬영 점수</span>
              <strong>{score}</strong>
              <span>/ 100점</span>
            </article>
          )}
        </div>}

        <div className={`notice ${!hasDetection ? 'retry-notice' : ''}`}>
          <strong>{!hasDetection ? '촬영 품질을 확인해 주세요' : hasCavity ? '지속되면 치과 상담을 권장해요' : '좋은 상태를 유지하고 있어요'}</strong>
          <br />
          {!hasDetection
            ? '사진이 흔들리거나 어두우면 치아 영역을 인식하기 어려워요.'
            : hasCavity
            ? '이 결과는 AI 참고 지표입니다. 통증이나 변화가 지속되면 치과에서 정확한 진단을 받아보세요.'
            : '꾸준한 관리로 건강한 치아 상태를 유지해 주세요.'}
        </div>
        {!hasDetection && <button className="login-button result-retry" onClick={() => onNavigate('camera')}>다시 촬영하기</button>}
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
