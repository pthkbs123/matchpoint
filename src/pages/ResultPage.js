import { resolveAnalysisFeedback } from '../analysisFeedback';
import { isCharacterFeedbackEnabled } from '../feedbackSettings';
import FeedbackCharacter from '../components/FeedbackCharacter';

function hasMetricValue(value) {
  return value !== null && value !== undefined && value !== '';
}

function formatMetricValue(value) {
  const number = Number(value);
  return Number.isFinite(number) ? Math.round(number) : value;
}

function ResultPage({ onNavigate, analysisResult, capturedUrl }) {
  const summary = analysisResult?.summary || {};
  const cavityCount = summary.cavity_count ?? 0;
  const normalCount = summary.normal_count ?? 0;
  const score = summary.overall_score ?? summary.score;
  const yellowingIndex = summary.yellowing_index;
  const gumInflammationIndex = summary.gum_inflammation_index;
  const colorBaseline = analysisResult?.color_baseline;
  const requiredBaselineSamples = colorBaseline?.required_samples ?? 3;
  const yellowingBaseline = colorBaseline?.yellowing;
  const gumBaseline = colorBaseline?.gum;
  const isPersonalBaseline = colorBaseline?.source === 'personal';
  const isBaselineCalibrating = isPersonalBaseline
    && (!yellowingBaseline?.ready || !gumBaseline?.ready);
  const detections = analysisResult?.detections || [];
  const captureQuality = analysisResult?.capture_quality;
  const isRejectedCapture = captureQuality?.valid === false;
  const visibleDetections = isRejectedCapture ? [] : detections;
  const feedback = resolveAnalysisFeedback(analysisResult);
  const hasCavity = feedback.type === 'cavity_alert';
  const hasDetection = visibleDetections.length > 0;
  const showAnalysisMetrics = !isRejectedCapture && hasDetection;
  const hasScore = hasMetricValue(score);
  const imageSize = analysisResult?.image_size;
  const characterFeedbackEnabled = isCharacterFeedbackEnabled();

  return (
    <section className="phone">
      <div className="page-content result-page-content">
        <div className="top-row">
          <button className="back-button" onClick={() => onNavigate('home')}>← 홈</button>
          <button className="text-button" onClick={() => onNavigate('report')}>리포트 보기</button>
        </div>

        {characterFeedbackEnabled ? (
          <section
            className={`child-feedback-card ${feedback.type}`}
            data-feedback-event={feedback.sound_event}
            aria-labelledby="child-feedback-title"
          >
            <span className="child-feedback-badge">어린이 구강 탐험 결과</span>
            <FeedbackCharacter type={feedback.type} />
            <h1 id="child-feedback-title">{feedback.title}</h1>
            <p>{feedback.message}</p>
          </section>
        ) : (
          <section className={`plain-feedback-card ${feedback.type}`} aria-labelledby="plain-feedback-title">
            <span>{hasDetection ? (hasCavity ? '확인 필요' : '분석 완료') : '재촬영 필요'}</span>
            <h1 id="plain-feedback-title">{feedback.parentTitle}</h1>
            <p>{feedback.parentMessage}</p>
          </section>
        )}

        <section className="guardian-result-card" aria-labelledby="guardian-result-title">
          <div className="guardian-result-heading">
            <span>보호자 확인</span>
            <div>
              <h2 id="guardian-result-title">{feedback.parentTitle}</h2>
              <p>{feedback.parentMessage}</p>
            </div>
          </div>

          {capturedUrl && imageSize && (
            <div className="result-image">
              <img src={capturedUrl} alt="촬영한 사진" />
              {visibleDetections.map((d, index) => {
                const left = (d.box.x1 / imageSize.width) * 100;
                const top = (d.box.y1 / imageSize.height) * 100;
                const boxWidth = ((d.box.x2 - d.box.x1) / imageSize.width) * 100;
                const boxHeight = ((d.box.y2 - d.box.y1) / imageSize.height) * 100;
                return (
                  <span
                    key={`${d.class}-${index}`}
                    className={`detect-box ${d.class === 'cavity' ? 'cavity' : 'normal'}`}
                    style={{ left: `${left}%`, top: `${top}%`, width: `${boxWidth}%`, height: `${boxHeight}%` }}
                    title={`${d.class} ${(d.confidence * 100).toFixed(0)}%`}
                  />
                );
              })}
            </div>
          )}

          {hasDetection && (
            <p className="detection-summary">
              전체 인식 {visibleDetections.length}곳 · 정상으로 인식 {normalCount}곳
            </p>
          )}

          {showAnalysisMetrics && isBaselineCalibrating && (
            <section className="baseline-progress-card" aria-label="개인 색상 기준값 설정 진행률">
              <div>
                <strong>내 아이의 평소 상태를 확인하고 있어요</strong>
                <span>같은 조명과 각도로 3회 촬영하면 맞춤 비교가 시작돼요.</span>
              </div>
              <p>
                <span>치아 색상 기준</span>
                <b>{yellowingBaseline?.sample_count ?? 0}/{requiredBaselineSamples}</b>
              </p>
              <p>
                <span>잇몸 색상 기준</span>
                <b>{gumBaseline?.sample_count ?? 0}/{requiredBaselineSamples}</b>
              </p>
            </section>
          )}

          {showAnalysisMetrics && <div className="metric-grid result-metric-grid">
            <article className={`metric ${!hasScore ? 'pending' : Number(score) >= 80 ? 'good' : 'watch'}`}>
              <span>종합 점수</span>
              <strong>{hasScore ? formatMetricValue(score) : '준비 중'}</strong>
              <span>{hasScore ? '/ 100점' : '분석 결과 대기'}</span>
            </article>
            <article className={`metric ${hasCavity ? 'watch' : 'good'}`}>
              <span>충치 의심</span>
              <strong>{cavityCount}</strong>
              <span>개 부위</span>
            </article>
            <article className={`metric ${hasMetricValue(yellowingIndex) ? 'measured' : 'pending'}`}>
              <span>황변 변화</span>
              <strong>
                {hasMetricValue(yellowingIndex)
                  ? formatMetricValue(yellowingIndex)
                  : isPersonalBaseline
                    ? yellowingBaseline?.ready
                      ? '맞춤 기준 완료'
                      : `기준 촬영 ${yellowingBaseline?.sample_count ?? 0}/${requiredBaselineSamples}`
                    : '준비 중'}
              </strong>
              <span>
                {hasMetricValue(yellowingIndex)
                  ? '/ 100'
                  : isPersonalBaseline
                    ? yellowingBaseline?.ready ? '다음 촬영부터 비교' : '3회 촬영으로 설정'
                    : '색상 분석 예정'}
              </span>
            </article>
            <article className={`metric ${hasMetricValue(gumInflammationIndex) ? 'measured' : 'pending'}`}>
              <span>잇몸 변화</span>
              <strong>
                {hasMetricValue(gumInflammationIndex)
                  ? formatMetricValue(gumInflammationIndex)
                  : isPersonalBaseline
                    ? gumBaseline?.ready
                      ? '맞춤 기준 완료'
                      : `기준 촬영 ${gumBaseline?.sample_count ?? 0}/${requiredBaselineSamples}`
                    : '준비 중'}
              </strong>
              <span>
                {hasMetricValue(gumInflammationIndex)
                  ? '/ 100'
                  : isPersonalBaseline
                    ? gumBaseline?.ready ? '다음 촬영부터 비교' : '3회 촬영으로 설정'
                    : '색상 분석 예정'}
              </span>
            </article>
          </div>}

          <div className={`notice ${!showAnalysisMetrics ? 'retry-notice' : ''}`}>
            <strong>보호자 안내</strong>
            <br />
            {showAnalysisMetrics
              ? '이 결과는 건강 관리를 돕는 AI 참고 지표이며 의료 진단을 대신하지 않습니다.'
              : '이번 사진은 분석 결과와 개인 기준값에 반영하지 않습니다.'}
          </div>

          {!showAnalysisMetrics && (
            <button className="login-button result-retry" onClick={() => onNavigate('camera')}>
              다시 촬영하기
            </button>
          )}
        </section>
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
