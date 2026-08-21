import { resolveAnalysisFeedback } from './analysisFeedback';

test('정상 감지 결과를 건강 피드백으로 변환한다', () => {
  const feedback = resolveAnalysisFeedback({
    detections: [{ class: 'normal' }],
    summary: { cavity_count: 0 },
  });

  expect(feedback.type).toBe('healthy');
  expect(feedback.sound_event).toBe('HEALTHY');
});

test('충치 의심 결과를 경고 피드백으로 변환한다', () => {
  const feedback = resolveAnalysisFeedback({
    detections: [{ class: 'cavity' }],
    summary: { cavity_count: 1 },
  });

  expect(feedback.type).toBe('cavity_alert');
  expect(feedback.character).toBe('cavity_monster');
});

test('치아가 감지되지 않으면 재촬영 피드백을 만든다', () => {
  const feedback = resolveAnalysisFeedback({ detections: [], summary: {} });

  expect(feedback.type).toBe('capture_retry');
  expect(feedback.sound_event).toBe('CAPTURE_RETRY');
});

test('백엔드가 보낸 유효한 피드백을 우선 사용한다', () => {
  const feedback = resolveAnalysisFeedback({
    detections: [{ class: 'normal' }],
    summary: { cavity_count: 0 },
    feedback: {
      type: 'cavity_alert',
      title: '서버에서 정한 안내',
      sound_event: 'MONSTER_FOUND',
    },
  });

  expect(feedback.type).toBe('cavity_alert');
  expect(feedback.title).toBe('서버에서 정한 안내');
  expect(feedback.sound_event).toBe('MONSTER_FOUND');
});

test('알 수 없는 피드백 타입은 분석 결과 기반 기본값으로 되돌린다', () => {
  const feedback = resolveAnalysisFeedback({
    detections: [{ class: 'normal' }],
    summary: { cavity_count: 0 },
    feedback: { type: 'unknown_type' },
  });

  expect(feedback.type).toBe('healthy');
});
