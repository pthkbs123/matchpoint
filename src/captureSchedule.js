export const captureSchedules = [
  {
    key: 'preschool',
    ageLabel: '만 6세 이하',
    feature: '유치열기 · 보호자 주도 관리가 중요한 시기',
    intervalDays: 7,
    intervalLabel: '주 1회',
    scheduleLabel: '매주 일요일',
  },
  {
    key: 'school',
    ageLabel: '만 7세 ~ 12세',
    feature: '혼합치열기 · 영구치가 맹출하고 교체되는 시기',
    intervalDays: 14,
    intervalLabel: '월 2회',
    scheduleLabel: '매월 1일·15일',
    rangeLabel: '2주 ~ 1개월에 1회',
  },
  {
    key: 'teen',
    ageLabel: '만 13세 이상',
    feature: '영구치열기 · 비교적 완만하게 변화를 관찰하는 시기',
    intervalDays: 30,
    intervalLabel: '월 1회',
    scheduleLabel: '매월 1일',
    rangeLabel: '1개월 ~ 3개월에 1회',
  },
];

export const captureWeekdays = [
  { value: 0, shortLabel: '월', label: '월요일' },
  { value: 1, shortLabel: '화', label: '화요일' },
  { value: 2, shortLabel: '수', label: '수요일' },
  { value: 3, shortLabel: '목', label: '목요일' },
  { value: 4, shortLabel: '금', label: '금요일' },
  { value: 5, shortLabel: '토', label: '토요일' },
  { value: 6, shortLabel: '일', label: '일요일' },
];

export function calculateAge(birthDate, today = new Date()) {
  if (!birthDate) return null;
  const [year, month, day] = birthDate.split('-').map(Number);
  if (!year || !month || !day) return null;
  let age = today.getFullYear() - year;
  const birthdayPassed = today.getMonth() + 1 > month
    || (today.getMonth() + 1 === month && today.getDate() >= day);
  if (!birthdayPassed) age -= 1;
  return Math.max(0, age);
}

export function getCaptureSchedule(birthDate, reminderWeekday = null) {
  const age = calculateAge(birthDate);
  if (age == null || age <= 6) {
    const parsedWeekday = reminderWeekday == null ? NaN : Number(reminderWeekday);
    const weekday = Number.isInteger(parsedWeekday) && parsedWeekday >= 0 && parsedWeekday <= 6
      ? parsedWeekday
      : 6;
    return {
      ...captureSchedules[0],
      age,
      reminderWeekday: weekday,
      scheduleLabel: `매주 ${captureWeekdays[weekday].label}`,
    };
  }
  if (age <= 12) return { ...captureSchedules[1], age };
  return { ...captureSchedules[2], age };
}
