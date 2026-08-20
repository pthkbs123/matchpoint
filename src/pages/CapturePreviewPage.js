function CapturePreviewPage({ onNavigate, onBack, capturedUrl }) {
  return (
    <section className="phone camera-screen">
      <div className="camera-view">
        <div className="camera-top">
          <button className="back-button dark-button" onClick={onBack || (() => onNavigate('camera'))}>← 재촬영</button>
          <span>촬영 완료</span>
        </div>
        {capturedUrl && <img src={capturedUrl} alt="촬영된 사진" className="camera-feed" />}
        <span className="preview-label">사진이 선명하게 촬영됐나요?</span>
        <div className="camera-guide" />
      </div>
      <div className="preview-actions">
        <button className="action" onClick={onBack || (() => onNavigate('camera'))}>다시 촬영</button>
        <button className="action primary" onClick={() => onNavigate('analyzing')}>이 사진 분석하기</button>
      </div>
    </section>
  );
}
export default CapturePreviewPage;
