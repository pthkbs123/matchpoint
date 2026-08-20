export function getNotificationReadKey(user, childId) {
  const userKey = user?.id || user?.email || 'current-user';
  const childKey = childId == null ? 'all' : childId;
  return `smileguard-notification-read:${userKey}:${childKey}`;
}

export function hasUnreadNotifications(notifications, user, childId) {
  if (!notifications?.length) return false;
  const lastReadId = localStorage.getItem(getNotificationReadKey(user, childId));
  return notifications[0].id !== lastReadId;
}

export function markNotificationsRead(notifications, user, childId) {
  if (!notifications?.length) return;
  localStorage.setItem(getNotificationReadKey(user, childId), notifications[0].id);
}
