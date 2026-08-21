import { useState } from 'react';
import { captureSchedules } from '../captureSchedule';

const steps = [
  { number: '1', title: '새 위생 커버를 씌워요', copy: '촬영할 때마다 일회용 커버를 새것으로 교체해 주세요.' },
  { number: '2', title: '렌즈와 LED를 확인해요', copy: '커버가 렌즈를 가리지 않고 LED가 켜지는지 확인해 주세요.' },
  { number: '3', title: '전체 치아가 화면에 보이게 해요', copy: '확대하지 말고 카메라에 보이는 전체 화각을 유지해 주세요.' },
  { number: '4', title: '사용한 커버는 바로 버려요', copy: '촬영이 끝난 뒤 커버를 제거하고 카메라 표면을 닦아 보관해 주세요.' },
];

const guideTabs = [
  { key: 'hygiene', label: '촬영 위생' },
  { key: 'schedule', label: '권장 주기' },
  { key: 'retry', label: '재촬영 기준' },
];

const retryReasons = [
  { icon: '≈', title: '사진이 흔들렸어요', copy: '치아 경계가 흐릿하면 카메라를 고정하고 다시 촬영해 주세요.' },
  { icon: '◐', title: '너무 어둡거나 밝아요', copy: 'LED 밝기와 렌즈 거리를 조절해 치아 색이 자연스럽게 보이게 해요.' },
  { icon: '⌗', title: '치아가 화면 밖으로 잘렸어요', copy: '확대하지 말고 확인할 치아 전체가 화면 안에 들어오게 해 주세요.' },
  { icon: '◌', title: '렌즈가 가려졌어요', copy: '물방울이나 위생 커버 주름을 정리한 뒤 다시 촬영해 주세요.' },
];

function CareGuidePage({ onNavigate, onBack }) {
  const [activeTab, setActiveTab] = useState('hygiene');

  return (
    <section className="phone">
      <div className="mypage-content">
        <div className="mypage-top">
          <button className="back-button" onClick={onBack || (() => onNavigate('home'))}>← 뒤로</button>
          <h1>촬영·위생 가이드</h1>
          <span className="mypage-top-space" />
        </div>

        <div className="guide-tabs" role="tablist" aria-label="촬영 가이드 항목">
          {guideTabs.map((tab) => (
            <button
              type="button"
              key={tab.key}
              id={`guide-tab-${tab.key}`}
              className={activeTab === tab.key ? 'active' : ''}
              role="tab"
              aria-selected={activeTab === tab.key}
              aria-controls={`guide-panel-${tab.key}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {activeTab === 'hygiene' && (
          <div className="guide-tab-panel" id="guide-panel-hygiene" role="tabpanel" aria-labelledby="guide-tab-hygiene">
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
          </div>
        )}

        {activeTab === 'schedule' && (
          <div className="guide-tab-panel" id="guide-panel-schedule" role="tabpanel" aria-labelledby="guide-tab-schedule">
            <div className="guide-section-heading">
              <span>◷</span>
              <div><h2>연령별 권장 촬영 주기</h2><p>아이의 성장 단계에 맞춰 무리 없이 기록해요.</p></div>
            </div>
            <section className="age-cycle-guide">
              <div className="age-cycle-table">
                {captureSchedules.map((schedule) => (
                  <article key={schedule.key}>
                    <span><strong>{schedule.ageLabel}</strong><small>{schedule.feature}</small></span>
                    <b>{schedule.scheduleLabel}</b>
                  </article>
                ))}
              </div>
              <p>자녀 생년월일을 기준으로 앱 안의 기본 촬영 일정이 자동 설정되며, 실제 치과 검진 주기와는 별개예요.</p>
            </section>
          </div>
        )}

        {activeTab === 'retry' && (
          <div className="guide-tab-panel" id="guide-panel-retry" role="tabpanel" aria-labelledby="guide-tab-retry">
            <div className="guide-section-heading retry">
              <span>↻</span>
              <div><h2>이럴 때는 다시 촬영해 주세요</h2><p>분석 전에 아래 네 가지를 확인해 주세요.</p></div>
            </div>
            <div className="retry-guide-list">
              {retryReasons.map((reason) => (
                <article key={reason.title}>
                  <span>{reason.icon}</span>
                  <div><strong>{reason.title}</strong><p>{reason.copy}</p></div>
                </article>
              ))}
            </div>
          </div>
        )}

        <p className="medical-disclaimer">SmileGuard 분석 결과는 의료진의 진단을 대신하지 않습니다. 통증·출혈·급격한 변화가 있으면 치과에 방문해 주세요.</p>
        <button className="login-button" onClick={() => onNavigate('pre-capture')}>촬영 준비하기</button>
      </div>
    </section>
  );
}

export default CareGuidePage;
