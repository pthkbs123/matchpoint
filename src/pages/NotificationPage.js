import { useEffect, useState } from 'react';

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

function NotificationPage({ onNavigate, onBack }) {
  const [serviceEnabled, setServiceEnabled] = useState(() => readBoolean('notif_service', true));
  const [reportEnabled, setReportEnabled] = useState(() => readBoolean('notif_report', true));
  const [nightModeEnabled, setNightModeEnabled] = useState(() => readBoolean('notif_night', true));
  const [reportDay, setReportDay] = useState(() => localStorage.getItem('notif_report_day') || '월요일');
  const [permission, setPermission] = useState(() => ('Notification' in window ? Notification.permission : 'unsupported'));

  useEffect(() => { localStorage.setItem('notif_service', String(serviceEnabled)); }, [serviceEnabled]);
  useEffect(() => { localStorage.setItem('notif_report', String(reportEnabled)); }, [reportEnabled]);
  useEffect(() => { localStorage.setItem('notif_night', String(nightModeEnabled)); }, [nightModeEnabled]);
  useEffect(() => { localStorage.setItem('notif_report_day', reportDay); }, [reportDay]);

  const requestPermission = async () => {
    if (!('Notification' in window)) return;
    const result = await Notification.requestPermission();
    setPermission(result);
  };

  const permissionCopy = {
    granted: '브라우저 알림이 허용되어 있어요.',
    denied: '브라우저 설정에서 알림 권한을 다시 허용해 주세요.',
    default: '주간 리포트를 받으려면 알림 권한이 필요해요.',
    unsupported: '현재 브라우저는 알림 기능을 지원하지 않아요.',
  }[permission];

  return (
    <section className="phone">
      <div className="mypage-content">
        <div className="mypage-top">
          <button className="back-button" onClick={onBack || (() => onNavigate('mypage'))}>← 뒤로</button>
          <h1>알림 설정</h1>
          <span className="mypage-top-space" />
        </div>

        <div className={`push-status ${permission}`}>
          <span>◌</span>
          <div><strong>Web Push 알림</strong><p>{permissionCopy}</p></div>
          {permission === 'default' && <button onClick={requestPermission}>허용</button>}
        </div>

        <div className="settings-list">
          <SettingRow title="상태 변화 알림" description="이전 기록보다 큰 변화가 감지되면 알려드려요." checked={serviceEnabled} onChange={setServiceEnabled} />
          <SettingRow title="주간 리포트" description="한 주간의 촬영 횟수와 점수 변화를 요약해요." checked={reportEnabled} onChange={setReportEnabled} />
          <SettingRow title="야간 알림 제한" description="오후 9시부터 오전 8시까지 알림을 보내지 않아요." checked={nightModeEnabled} onChange={setNightModeEnabled} />
        </div>

        <label className="report-day-field">
          <span><strong>주간 리포트 받는 날</strong><small>매주 선택한 요일 오전에 요약 알림을 보내요.</small></span>
          <select value={reportDay} onChange={(event) => setReportDay(event.target.value)} disabled={!reportEnabled}>
            {['월요일', '화요일', '수요일', '목요일', '금요일', '토요일', '일요일'].map((day) => <option key={day}>{day}</option>)}
          </select>
        </label>

        <section className="notification-history">
          <div className="card-head"><h2>알림 내역</h2><span>최근 30일</span></div>
          <div className="empty-notification"><span>✓</span><strong>새로운 주의 알림이 없어요</strong><p>변화가 감지되면 이곳에서 다시 확인할 수 있어요.</p></div>
        </section>
      </div>
    </section>
  );
}

export default NotificationPage;
