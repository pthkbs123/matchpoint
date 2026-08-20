import { hasUnreadNotifications, markNotificationsRead } from './notificationStorage';

beforeEach(() => localStorage.clear());

test('새 알림은 읽지 않은 상태로 표시하고 확인 후 읽음 처리한다', () => {
  const user = { id: 7 };
  const notifications = [{ id: 'child-3:2026-08-19' }];

  expect(hasUnreadNotifications(notifications, user, 3)).toBe(true);
  markNotificationsRead(notifications, user, 3);
  expect(hasUnreadNotifications(notifications, user, 3)).toBe(false);
});

test('알림이 없으면 읽지 않은 상태를 표시하지 않는다', () => {
  expect(hasUnreadNotifications([], { id: 7 }, 3)).toBe(false);
});
