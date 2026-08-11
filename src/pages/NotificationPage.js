import React, { useState, useEffect } from 'react';

function NotificationPage({ onNavigate }) {
  // 1. 서비스 & 리포트 알림 (핵심 서비스 알림)
  const [serviceEnabled, setServiceEnabled] = useState(() => {
    const saved = localStorage.getItem('notif_service');
    return saved !== null ? JSON.parse(saved) : true; // 기본값: true
  });

  // 2. 주간 리포트 알림 (기존 이메일 알림 대체)
  const [reportEnabled, setReportEnabled] = useState(() => {
    const saved = localStorage.getItem('notif_report');
    return saved !== null ? JSON.parse(saved) : false; // 기본값: false
  });

  // 3. 마케팅 정보 수신
  const [marketingEnabled, setMarketingEnabled] = useState(() => {
    const saved = localStorage.getItem('notif_marketing');
    return saved !== null ? JSON.parse(saved) : false; // 기본값: false
  });

  // 4. 야간 알림 제한 (법적 기준: 21시~08시)
  const [nightModeEnabled, setNightModeEnabled] = useState(() => {
    const saved = localStorage.getItem('notif_night');
    return saved !== null ? JSON.parse(saved) : true; // 기본값: true
  });

  // localStorage 자동 저장
  useEffect(() => {
    localStorage.setItem('notif_service', JSON.stringify(serviceEnabled));
  }, [serviceEnabled]);

  useEffect(() => {
    localStorage.setItem('notif_report', JSON.stringify(reportEnabled));
  }, [reportEnabled]);

  useEffect(() => {
    localStorage.setItem('notif_marketing', JSON.stringify(marketingEnabled));
  }, [marketingEnabled]);

  useEffect(() => {
    localStorage.setItem('notif_night', JSON.stringify(nightModeEnabled));
  }, [nightModeEnabled]);

  return (
    <section className="phone">
      <div className="mypage-content">
        
        {/* 상단 헤더 영역 */}
        <div className="mypage-top">
          <button 
            className="back-button" 
            onClick={() => onNavigate ? onNavigate('mypage') : window.history.back()}
          >
            ← 뒤로
          </button>
          <h1>알림 설정</h1>
          <span className="mypage-top-space" />
        </div>

        {/* 설정 항목 리스트 */}
        <div className="settings-list" style={{ marginTop: '10px' }}>
          
          {/* 1. 핵심 서비스 알림 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '1rem', color: '#111' }}>주요 기능 알림</div>
              <div style={{ fontSize: '0.825rem', color: '#767676', marginTop: '4px' }}>새로운 분석 결과 및 주요 기능 알림을 받습니다.</div>
            </div>
            <input 
              type="checkbox" 
              checked={serviceEnabled} 
              onChange={(e) => setServiceEnabled(e.target.checked)}
              style={{ width: '20px', height: '20px', accentColor: '#2563eb', cursor: 'pointer' }}
            />
          </div>

          {/* 2. 주간 리포트 알림 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '1rem', color: '#111' }}>주간 리포트 알림</div>
              <div style={{ fontSize: '0.825rem', color: '#767676', marginTop: '4px' }}>한 주간의 데이터 분석 및 요약 리포트를 알립니다.</div>
            </div>
            <input 
              type="checkbox" 
              checked={reportEnabled} 
              onChange={(e) => setReportEnabled(e.target.checked)}
              style={{ width: '20px', height: '20px', accentColor: '#2563eb', cursor: 'pointer' }}
            />
          </div>

          {/* 3. 마케팅 정보 수신 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0', borderBottom: '1px solid #f0f0f0' }}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '1rem', color: '#111' }}>마케팅 정보 수신</div>
              <div style={{ fontSize: '0.825rem', color: '#767676', marginTop: '4px' }}>이벤트, 혜택 및 신규 기능 소식을 받습니다.</div>
            </div>
            <input 
              type="checkbox" 
              checked={marketingEnabled} 
              onChange={(e) => setMarketingEnabled(e.target.checked)}
              style={{ width: '20px', height: '20px', accentColor: '#2563eb', cursor: 'pointer' }}
            />
          </div>

          {/* 4. 야간 알림 제한 */}
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '16px 0' }}>
            <div>
              <div style={{ fontWeight: '600', fontSize: '1rem', color: '#111' }}>야간 알림 제한</div>
              <div style={{ fontSize: '0.825rem', color: '#767676', marginTop: '4px' }}>야간 시간대(21:00 ~ 08:00) 알림 수신을 제한합니다.</div>
            </div>
            <input 
              type="checkbox" 
              checked={nightModeEnabled} 
              onChange={(e) => setNightModeEnabled(e.target.checked)}
              style={{ width: '20px', height: '20px', accentColor: '#2563eb', cursor: 'pointer' }}
            />
          </div>

        </div>
      </div>
    </section>
  );
}

export default NotificationPage;