export const FEEDBACK_TYPES = ['healthy', 'cavity_alert', 'capture_retry', 'analysis_error'];

const FEEDBACK_DEFAULTS = {
  healthy: {
    character: 'healthy_tooth',
    sound_event: 'HEALTHY',
    title: '오늘도 반짝이는 치아예요!',
    message: '지금처럼 꼼꼼하게 관리해 주세요.',
    parentTitle: '좋은 상태를 유지하고 있어요',
    parentMessage: '이번 촬영에서는 주의가 필요한 부위가 감지되지 않았어요.',
  },
  cavity_alert: {
    character: 'cavity_monster',
    sound_event: 'CAVITY_ALERT',
    title: '앗! 주의 깊게 볼 곳이 있어요',
    message: '보호자와 함께 표시된 곳을 확인해 봐요.',
    parentTitle: '지속되면 치과 상담을 권장해요',
    parentMessage: 'AI 참고 결과입니다. 같은 위치에서 반복되거나 통증·변화가 있으면 치과에서 정확한 진단을 받아보세요.',
  },
  capture_retry: {
    character: 'retry_tooth',
    sound_event: 'CAPTURE_RETRY',
    title: '치아가 잘 보이도록 한 번 더!',
    message: '화면 중앙에 치아를 맞추고 다시 촬영해 주세요.',
    parentTitle: '촬영 품질을 확인해 주세요',
    parentMessage: '사진이 흔들리거나 어두우면 치아 영역을 인식하기 어려워요.',
  },
  analysis_error: {
    character: 'retry_tooth',
    sound_event: 'ANALYSIS_ERROR',
    title: '분석을 마치지 못했어요',
    message: '잠시 후 다시 시도해 주세요.',
    parentTitle: '분석 연결을 확인해 주세요',
    parentMessage: '네트워크와 분석 서버 상태를 확인한 뒤 다시 촬영해 주세요.',
  },
};

export function resolveAnalysisFeedback(analysisResult) {
  const detections = analysisResult?.detections || [];
  const cavityCount = analysisResult?.summary?.cavity_count ?? 0;
  const fallbackType = detections.length === 0
    ? 'capture_retry'
    : cavityCount > 0
      ? 'cavity_alert'
      : 'healthy';
  const backendFeedback = analysisResult?.feedback;
  const requestedType = backendFeedback?.type;
  const type = FEEDBACK_TYPES.includes(requestedType) ? requestedType : fallbackType;

  const resolved = {
    ...FEEDBACK_DEFAULTS[type],
    ...(backendFeedback || {}),
  };
  return { ...resolved, type };
}
