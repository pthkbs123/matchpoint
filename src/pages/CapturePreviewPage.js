function CapturePreviewPage({ onNavigate, onBack, capturedUrl, onRotate }) {
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
        <div className="preview-rotation-actions" aria-label="사진 방향 조정">
          <button type="button" onClick={() => onRotate?.(-90)}>↶ 왼쪽 회전</button>
          <button type="button" onClick={() => onRotate?.(90)}>오른쪽 회전 ↷</button>
        </div>
      </div>
      <div className="preview-actions">
        <button className="action" onClick={onBack || (() => onNavigate('camera'))}>다시 촬영</button>
        <button className="action primary" onClick={() => onNavigate('analyzing')}>이 사진 분석하기</button>
      </div>
    </section>
  );
}
export default CapturePreviewPage;
