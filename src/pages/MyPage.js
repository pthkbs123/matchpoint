function MyPage({ onNavigate }) {
  const menuItems = [
    { icon: '◎', title: '내 정보 관리', description: '이름과 프로필을 수정해요' },
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
            <img src="/profile-avatar.svg" alt="한이음 님 프로필" />
            <button type="button" className="profile-edit" aria-label="프로필 사진 변경">
              ✎
            </button>
          </div>
          <h2>한이음 님</h2>
          <p>hani@example.com</p>
          <span className="profile-status">SmileGuard와 함께한 지 24일째</span>
        </div>

        <div className="mypage-summary">
          <div><strong>84</strong><span>현재 점수</span></div>
          <div><strong>7회</strong><span>누적 측정</span></div>
          <div><strong>3주</strong><span>연속 관리</span></div>
        </div>

        <div className="mypage-menu">
          {menuItems.map((item) => (
            <button type="button" className="mypage-menu-item" key={item.title}>
              <span className="mypage-menu-icon">{item.icon}</span>
              <span className="mypage-menu-copy">
                <strong>{item.title}</strong>
                <small>{item.description}</small>
              </span>
              <span className="mypage-menu-arrow">›</span>
            </button>
          ))}
        </div>

        <button type="button" className="logout-button" onClick={() => onNavigate('login')}>
          로그아웃
        </button>
      </div>
    </section>
  );
}

export default MyPage;
