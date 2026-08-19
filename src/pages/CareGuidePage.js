const steps = [
  { number: '1', title: '새 위생 커버를 씌워요', copy: '촬영할 때마다 일회용 커버를 새것으로 교체해 주세요.' },
  { number: '2', title: '렌즈와 LED를 확인해요', copy: '커버가 렌즈를 가리지 않고 LED가 켜지는지 확인해 주세요.' },
  { number: '3', title: '치아를 가이드 안에 맞춰요', copy: '카메라를 천천히 움직이고 치아가 화면 중앙에 오도록 맞춰 주세요.' },
  { number: '4', title: '사용한 커버는 바로 버려요', copy: '촬영이 끝난 뒤 커버를 제거하고 카메라 표면을 닦아 보관해 주세요.' },
];

function CareGuidePage({ onNavigate }) {
  return (
    <section className="phone">
      <div className="mypage-content">
        <div className="mypage-top">
          <button className="back-button" onClick={() => onNavigate('mypage')}>← 뒤로</button>
          <h1>촬영·위생 가이드</h1>
          <span className="mypage-top-space" />
        </div>

        <div className="guide-hero">
          <span>✦</span>
          <h2>안전하고 선명하게 촬영해요</h2>
          <p>위생 커버와 촬영 품질을 확인하면 분석 결과의 일관성을 높일 수 있어요.</p>
        </div>

        <ol className="guide-steps">
          {steps.map((step) => (
            <li key={step.number}>
              <span>{step.number}</span>
              <div><strong>{step.title}</strong><p>{step.copy}</p></div>
            </li>
          ))}
        </ol>

        <div className="safety-note">
          <strong>이럴 때는 다시 촬영해 주세요</strong>
          <ul>
            <li>사진이 흔들리거나 너무 어두운 경우</li>
            <li>치아가 화면 밖으로 잘린 경우</li>
            <li>물방울이나 커버 주름이 렌즈를 가린 경우</li>
          </ul>
        </div>

        <p className="medical-disclaimer">SmileGuard 분석 결과는 의료진의 진단을 대신하지 않습니다. 통증·출혈·급격한 변화가 있으면 치과에 방문해 주세요.</p>
        <button className="login-button" onClick={() => onNavigate('camera')}>촬영하러 가기</button>
      </div>
    </section>
  );
}

export default CareGuidePage;
