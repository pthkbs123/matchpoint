import { formatPhoneNumber, isValidPhoneNumber, normalizePhoneNumber } from './phone';

test('휴대폰 번호는 숫자만 저장할 수 있도록 정규화한다', () => {
  expect(normalizePhoneNumber('010-1234-5678')).toBe('01012345678');
});

test('휴대폰 번호를 화면 표시 형식으로 변환한다', () => {
  expect(formatPhoneNumber('01012345678')).toBe('010-1234-5678');
});

test('010으로 시작하는 11자리 번호만 허용한다', () => {
  expect(isValidPhoneNumber('010-1234-5678')).toBe(true);
  expect(isValidPhoneNumber('02-1234-5678')).toBe(false);
});
