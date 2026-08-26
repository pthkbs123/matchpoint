import { calculateAge, getCaptureSchedule } from './captureSchedule';

test('생일이 지나지 않은 아동의 만 나이를 계산한다', () => {
  expect(calculateAge('2020-12-01', new Date(2026, 7, 21))).toBe(5);
});

test('만 6세 이하는 주 1회 주기를 적용한다', () => {
  expect(getCaptureSchedule('2020-01-01').intervalDays).toBe(7);
});

test('만 7세부터 12세까지는 2주 주기를 적용한다', () => {
  const birthYear = new Date().getFullYear() - 9;
  expect(getCaptureSchedule(`${birthYear}-01-01`).scheduleLabel).toBe('2주에 한번');
});

test('생년월일과 요일 설정이 없으면 등록한 날의 요일로 주 1회를 적용한다', () => {
  expect(getCaptureSchedule(null, null, new Date(2026, 7, 25)).scheduleLabel).toBe('매주 화요일');
});

test('만 6세 이하 자녀는 선택한 촬영 요일을 적용한다', () => {
  expect(getCaptureSchedule(null, 2).scheduleLabel).toBe('매주 수요일');
});

test('만 13세 이상은 매월 1일 일정을 적용한다', () => {
  const birthYear = new Date().getFullYear() - 14;
  expect(getCaptureSchedule(`${birthYear}-01-01`).scheduleLabel).toBe('월 1회');
});
