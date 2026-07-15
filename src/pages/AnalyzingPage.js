import { useEffect } from 'react';
function AnalyzingPage({ onNavigate }) {
  useEffect(()=>{ const timer=setTimeout(()=>onNavigate('result'),2200); return()=>clearTimeout(timer); },[onNavigate]);
  return <section className="phone center-page"><div className="loader"/><p className="eyebrow">AI ANALYSIS</p><h1>구강 상태를 분석하고 있어요</h1><p className="subtext">치아 영역과 잇몸 색상을 확인 중입니다.<br/>잠시만 기다려 주세요.</p><div className="progress"><span/></div></section>;
}
export default AnalyzingPage;
