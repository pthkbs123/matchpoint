import { fireEvent, render, screen } from '@testing-library/react';
import { setCharacterFeedbackEnabled } from '../feedbackSettings';
import ResultPage from './ResultPage';

const cavityResult = {
  image_size: { width: 1000, height: 700 },
  detections: [
    { class: 'cavity', confidence: 0.91, box: { x1: 100, y1: 120, x2: 260, y2: 310 } },
    { class: 'normal', confidence: 0.88, box: { x1: 300, y1: 120, x2: 460, y2: 310 } },
  ],
  summary: {
    cavity_count: 1,
    normal_count: 1,
    score: 82,
  },
};

beforeEach(() => {
  localStorage.removeItem('smileguard-character-feedback-enabled');
  localStorage.removeItem('smileguard-child-feedback-settings');
});

test('어린이용 충치 피드백과 보호자용 4개 지표를 분리해 보여준다', () => {
  const { container } = render(
    <ResultPage
      onNavigate={jest.fn()}
      analysisResult={cavityResult}
      capturedUrl="blob:test-image"
    />
  );

  expect(screen.getByText('앗! 주의 깊게 볼 곳이 있어요')).toBeInTheDocument();
  expect(screen.getByText('보호자 확인')).toBeInTheDocument();
  expect(screen.getByText('종합 점수')).toBeInTheDocument();
  expect(screen.getByText('충치 의심')).toBeInTheDocument();
  expect(screen.getByText('황변 변화')).toBeInTheDocument();
  expect(screen.getByText('잇몸 변화')).toBeInTheDocument();
  expect(screen.getAllByText('준비 중')).toHaveLength(2);
  expect(container.querySelector('[data-feedback-event="CAVITY_ALERT"]')).toBeInTheDocument();
});

test('백엔드가 색상 지표를 보내면 실제 값으로 바꿔 표시한다', () => {
  render(
    <ResultPage
      onNavigate={jest.fn()}
      analysisResult={{
        ...cavityResult,
        summary: {
          ...cavityResult.summary,
          yellowing_index: 23.6,
          gum_inflammation_index: 17.2,
        },
      }}
    />
  );

  expect(screen.getByText('24')).toBeInTheDocument();
  expect(screen.getByText('17')).toBeInTheDocument();
  expect(screen.queryByText('준비 중')).not.toBeInTheDocument();
});

test('치아가 감지되지 않으면 재촬영 안내와 이동 버튼을 표시한다', () => {
  const onNavigate = jest.fn();
  render(
    <ResultPage
      onNavigate={onNavigate}
      analysisResult={{ detections: [], summary: {} }}
    />
  );

  expect(screen.getByText('치아가 잘 보이도록 한 번 더!')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '다시 촬영하기' }));
  expect(onNavigate).toHaveBeenCalledWith('camera');
});

test('구강 사진이 아니면 오탐 박스와 성능 지표를 표시하지 않는다', () => {
  const { container } = render(
    <ResultPage
      onNavigate={jest.fn()}
      capturedUrl="blob:invalid-image"
      analysisResult={{
        image_size: { width: 1000, height: 700 },
        detections: cavityResult.detections,
        summary: { cavity_count: 2, normal_count: 0, score: 70 },
        capture_quality: { valid: false, code: 'insufficient_tooth_regions' },
        feedback: {
          type: 'capture_retry',
          parentTitle: '구강 사진을 확인해 주세요',
          parentMessage: '치아 영역이 충분히 확인되지 않아 분석 결과를 저장하지 않았습니다.',
        },
      }}
    />
  );

  expect(screen.getByText('구강 사진을 확인해 주세요')).toBeInTheDocument();
  expect(screen.getByText('이번 사진은 분석 결과와 개인 기준값에 반영하지 않습니다.')).toBeInTheDocument();
  expect(screen.queryByText('종합 점수')).not.toBeInTheDocument();
  expect(screen.queryByText('충치 의심')).not.toBeInTheDocument();
  expect(container.querySelector('.detect-box')).not.toBeInTheDocument();
  expect(screen.getByRole('button', { name: '다시 촬영하기' })).toBeInTheDocument();
});

test('공통 설정에서 캐릭터 피드백을 끄면 일반 결과 안내를 표시한다', () => {
  setCharacterFeedbackEnabled(false);
  const { container } = render(
    <ResultPage
      onNavigate={jest.fn()}
      analysisResult={cavityResult}
    />
  );

  expect(container.querySelector('.feedback-character')).not.toBeInTheDocument();
  expect(container.querySelector('[data-feedback-event]')).not.toBeInTheDocument();
  expect(screen.getByText('확인 필요')).toBeInTheDocument();
});

test('개인 LAB 기준값이 3회 미만이면 설정 진행률을 표시한다', () => {
  render(
    <ResultPage
      onNavigate={jest.fn()}
      analysisResult={{
        ...cavityResult,
        summary: {
          ...cavityResult.summary,
          yellowing_index: null,
          gum_inflammation_index: null,
        },
        color_baseline: {
          source: 'personal',
          required_samples: 3,
          yellowing: { sample_count: 2, ready: false },
          gum: { sample_count: 1, ready: false },
        },
      }}
    />
  );

  expect(screen.getByText('내 아이의 평소 상태를 확인하고 있어요')).toBeInTheDocument();
  expect(screen.getByText('기준 촬영 2/3')).toBeInTheDocument();
  expect(screen.getByText('기준 촬영 1/3')).toBeInTheDocument();
});

test('세 번째 촬영으로 기준값을 완성하면 다음 촬영부터 비교한다고 안내한다', () => {
  render(
    <ResultPage
      onNavigate={jest.fn()}
      analysisResult={{
        ...cavityResult,
        summary: {
          ...cavityResult.summary,
          yellowing_index: null,
          gum_inflammation_index: null,
        },
        color_baseline: {
          source: 'personal',
          required_samples: 3,
          yellowing: { sample_count: 3, ready: true, comparison_available: false },
          gum: { sample_count: 3, ready: true, comparison_available: false },
        },
      }}
    />
  );

  expect(screen.getAllByText('맞춤 기준 완료')).toHaveLength(2);
  expect(screen.getAllByText('다음 촬영부터 비교')).toHaveLength(2);
});
