function CameraPage({ onNavigate }) {
  return <section className="phone camera-screen"><div className="camera-view"><div className="camera-top"><button className="back-button dark-button" onClick={()=>onNavigate('home')}>← 뒤로</button><span>LIVE</span></div><p className="camera-hint">치아가 가이드 안에 들어오도록 맞춰주세요</p><div className="camera-guide" /></div><div className="camera-controls"><button className="control-link" onClick={()=>onNavigate('home')}>뒤로가기</button><button className="shutter" onClick={()=>onNavigate('preview')} aria-label="촬영"/><button className="control-link" onClick={()=>onNavigate('home')}>홈</button></div></section>;
}
export default CameraPage;
