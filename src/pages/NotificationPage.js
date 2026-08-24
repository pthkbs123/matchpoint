import { useEffect, useState } from 'react';
import { apiFetch } from '../api';
import { markNotificationsRead } from '../notificationStorage';

function readBoolean(key, fallback) {
  const value = localStorage.getItem(key);
  return value == null ? fallback : value === 'true';
}

function SettingRow({ title, description, checked, onChange }) {
  return (
    <label className="setting-row">
      <span><strong>{title}</strong><small>{description}</small></span>
      <input type="checkbox" checked={checked} onChange={(event) => onChange(event.target.checked)} />
      <i aria-hidden="true" />
    </label>
  );
}

function isNotificationVisible(notification, settings) {
  if (notification.type === 'capture_due') return settings.captureReminderEnabled;
  if (notification.type === 'monthly_report') return settings.monthlyReportEnabled;
  return settings.serviceEnabled;
}

function NotificationPage({ onNavigate, onBack, onOpenMonthlyReport, user, token, selectedChildId }) {
  const [serviceEnabled, setServiceEnabled] = useState(() => readBoolean('notif_service', true));
  const [captureReminderEnabled, setCaptureReminderEnabled] = useState(() => readBoolean('notif_capture', true));
  const [monthlyReportEnabled, setMonthlyReportEnabled] = useState(() => readBoolean('notif_monthly_report', true));
  const [notifications, setNotifications] = useState([]);
  const [scheduleLabel, setScheduleLabel] = useState('매주 일요일');
  const [isLoadingNotifications, setIsLoadingNotifications] = useState(true);

  useEffect(() => { localStorage.setItem('notif_service', String(serviceEnabled)); }, [serviceEnabled]);
  useEffect(() => { localStorage.setItem('notif_capture', String(captureReminderEnabled)); }, [captureReminderEnabled]);
  useEffect(() => { localStorage.setItem('notif_monthly_report', String(monthlyReportEnabled)); }, [monthlyReportEnabled]);

  useEffect(() => {
    if (!token) {
      setIsLoadingNotifications(false);
      return undefined;
    }

    let cancelled = false;
    const query = selectedChildId ? `?child_id=${selectedChildId}` : '';
    apiFetch(`/api/report/summary${query}`, { token })
      .then((data) => {
        if (cancelled) return;
        const nextNotifications = data.notifications || [];
        setNotifications(nextNotifications);
        setScheduleLabel(data.notification_schedule_label || '매주 일요일');
      })
      .catch(() => { if (!cancelled) setNotifications([]); })
      .finally(() => { if (!cancelled) setIsLoadingNotifications(false); });

    return () => { cancelled = true; };
  }, [token, selectedChildId]);

  const visibleNotifications = notifications.filter((notification) => (
    isNotificationVisible(notification, {
      captureReminderEnabled,
      monthlyReportEnabled,
      serviceEnabled,
    })
  ));

  useEffect(() => {
    markNotificationsRead(visibleNotifications, user, selectedChildId);
  }, [notifications, user, selectedChildId, captureReminderEnabled, monthlyReportEnabled, serviceEnabled]); // eslint-disable-line react-hooks/exhaustive-deps

  const notificationHistory = (
    <section className="notification-history">
      <div className="card-head"><h2>알림 내역</h2><span>최근 30일</span></div>
      {isLoadingNotifications ? (
        <p className="page-state">알림 내역을 불러오는 중이에요...</p>
      ) : visibleNotifications.length > 0 ? (
        <div className="notification-history-list">
          {visibleNotifications.map((notification) => (
            <article className={`notification-history-item ${notification.type === 'monthly_report' ? 'monthly-report' : ''}`} key={notification.id}>
              <span className="notification-history-icon">
                {notification.type === 'capture_due' ? '◷' : notification.type === 'monthly_report' ? '▥' : '!'}
              </span>
              <div>
                <small>{notification.date_label}</small>
                <strong>{notification.title}</strong>
                <p>{notification.message}</p>
              </div>
              {notification.type === 'monthly_report' ? (
                <button
                  type="button"
                  className="notification-report-button"
                  onClick={() => onOpenMonthlyReport
                    ? onOpenMonthlyReport(notification.report_month)
                    : onNavigate('monthly-report')}
                >
                  보기 ›
                </button>
              ) : notification.score_change != null && <b>{notification.score_change}점</b>}
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-notification"><span>✓</span><strong>새로운 앱 내 알림이 없어요</strong><p>촬영 일정이나 상태 변화가 감지되면 이곳에서 확인할 수 있어요.</p></div>
      )}
    </section>
  );

  return (
    <section className="phone">
      <div className="mypage-content">
        <div className="mypage-top">
          <button className="back-button" onClick={onBack || (() => onNavigate('mypage'))}>← 뒤로</button>
          <h1>알림</h1>
          <span className="mypage-top-space" />
        </div>

        {notificationHistory}

        <div className="in-app-notice-status">
          <span>◷</span>
          <div><strong>맞춤 촬영 일정</strong><p>{scheduleLabel} · 앱을 열면 촬영 시기를 알려드려요.</p></div>
        </div>

        <div className="settings-list">
          <SettingRow title="촬영 일정 알림" description={`${scheduleLabel} 일정에 맞춰 앱 안에서 알려드려요.`} checked={captureReminderEnabled} onChange={setCaptureReminderEnabled} />
          <SettingRow title="월간 리포트" description="매월 지난달 촬영 횟수와 평균 변화를 정리해 드려요." checked={monthlyReportEnabled} onChange={setMonthlyReportEnabled} />
          <SettingRow title="상태 변화 알림" description="이전 기록보다 큰 변화가 감지되면 알려드려요." checked={serviceEnabled} onChange={setServiceEnabled} />
        </div>
      </div>
    </section>
  );
}

export default NotificationPage;
