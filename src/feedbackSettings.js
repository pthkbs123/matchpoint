const STORAGE_KEY = 'smileguard-character-feedback-enabled';
const LEGACY_STORAGE_KEY = 'smileguard-child-feedback-settings';

export function isCharacterFeedbackEnabled() {
  const value = localStorage.getItem(STORAGE_KEY);
  if (value != null) return value === 'true';

  try {
    const legacySettings = JSON.parse(localStorage.getItem(LEGACY_STORAGE_KEY) || '{}');
    const legacyValues = Object.values(legacySettings);
    if (legacyValues.length > 0) return !legacyValues.includes(false);
  } catch {
    // 이전 자녀별 설정을 읽지 못하면 기본 설정을 사용합니다.
  }

  return true;
}

export function setCharacterFeedbackEnabled(enabled) {
  const nextValue = Boolean(enabled);
  try {
    localStorage.setItem(STORAGE_KEY, String(nextValue));
    localStorage.removeItem(LEGACY_STORAGE_KEY);
  } catch {
    // 저장소 사용이 제한된 환경에서는 현재 화면의 상태만 유지합니다.
  }
  return nextValue;
}
