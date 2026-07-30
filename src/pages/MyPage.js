import { useEffect, useState } from 'react';
import { apiFetch } from '../api';

function MyPage({ onNavigate, onLogout, user, token }) {
  const userName = user?.name || user?.nickname || '한이음';
  const userEmail = user?.email || 'hani@example.com';
  const profileImage = user?.picture || user?.profileImage || '/profile-avatar.svg';
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    if (!token) return;
    let cancelled = false;
    apiFetch('/api/report/summary', { token })
      .then((data) => { if (!cancelled) setSummary(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [token]);

  const menuItems = [
    { icon: '◎', title: '내 정보 관리', description: '이름과 프로필을 수정해요' },
    { icon: '⏱', title: '촬영 히스토리', description: '자녀별 촬영 기록을 확인해요', onClick: () => onNavigate('history') },
    { icon: '◇', title: '기준값 관리', description: '구강 분석 기준값을 확인하고 재설정해요' },
    { icon: '♧', title: '알림 설정', description: '주간 리포트와 주의 알림을 관리해요' },
  ];

  return (
    <section className="phone">
      <div className="mypage-content">
        <div className="mypage-top">
          <button className="back-button" onClick={() => onNavigate('home')}>
            ← 뒤로
          </button>
          <h1>마이페이지</h1>
          <span className="mypage-top-space" />
        </div>

        <div className="profile-card">
          <div className="profile-image-wrap">
            <img src={profileImage} alt={`${userName} 님 프로필`} />
            <button type="button" className="profile-edit" aria-label="프로필 사진 변경">
              ✎
            </button>
          </div>
          <h2>{userName} 님</h2>
          <p>{userEmail}</p>
          <span className="profile-status">SmileGuard와 함께한 지 {summary?.member_since_days ?? 0}일째</span>
        </div>

        <div className="mypage-summary">
          <div><strong>{summary?.current_score ?? 100}</strong><span>현재 점수</span></div>
          <div><strong>{summary?.total_scans ?? 0}회</strong><span>누적 측정</span></div>
          <div><strong>{summary?.streak_days ?? 0}일</strong><span>연속 관리</span></div>
        </div>

        <div className="mypage-menu">
          {menuItems.map((item) => (
            <button type="button" className="mypage-menu-item" key={item.title} onClick={item.onClick}>
              <span className="mypage-menu-icon">{item.icon}</span>
              <span className="mypage-menu-copy">
                <strong>{item.title}</strong>
                <small>{item.description}</small>
              </span>
              <span className="mypage-menu-arrow">›</span>
            </button>
          ))}
        </div>

        <button type="button" className="logout-button" onClick={onLogout}>
          로그아웃
        </button>
      </div>
    </section>
  );
}

export default MyPage;
