import { isCharacterFeedbackEnabled, setCharacterFeedbackEnabled } from './feedbackSettings';

beforeEach(() => {
  localStorage.removeItem('smileguard-character-feedback-enabled');
  localStorage.removeItem('smileguard-child-feedback-settings');
});

test('캐릭터 피드백은 기본적으로 켜져 있다', () => {
  expect(isCharacterFeedbackEnabled()).toBe(true);
});

test('한 번 변경한 캐릭터 피드백 설정을 공통으로 저장한다', () => {
  setCharacterFeedbackEnabled(false);
  expect(isCharacterFeedbackEnabled()).toBe(false);

  setCharacterFeedbackEnabled(true);
  expect(isCharacterFeedbackEnabled()).toBe(true);
});

test('기존 자녀별 설정 중 꺼진 값이 있으면 공통 설정도 꺼짐으로 이어받는다', () => {
  localStorage.setItem('smileguard-child-feedback-settings', JSON.stringify({ 1: true, 2: false }));
  expect(isCharacterFeedbackEnabled()).toBe(false);
});
