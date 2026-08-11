import React, { useState } from 'react';

function EditProfilePage({ onNavigate }) {
  // 1. 프로필 정보 상태 관리 (localStorage 연동)
  const [userName, setUserName] = useState(() => {
    return localStorage.getItem('user_name') || '성지혜';
  });

  // 2. 이메일 계정 (표시용 - 수정 불가)
  const [userEmail] = useState('jihye.sung@example.com');

  // 3. 소셜 연동 상태 (localStorage에서 불러오거나 기본값 설정)
  // 예시: 'kakao', 'google', 'both', 'none'
  const [provider] = useState(() => {
    return localStorage.getItem('auth_provider') || 'kakao'; // 테스트용 기본값 'kakao'
  });

  // 4. 전화번호 (localStorage 연동)
  const [userPhone, setUserPhone] = useState(() => {
    return localStorage.getItem('user_phone') || '010-1234-5678';
  });

  // 5. 비밀번호 변경 모달/영역 상태
  const [isChangingPassword, setIsChangingPassword] = useState(false);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // 소셜 연동 텍스트 및 색상 변환 함수
  const renderSocialStatus = () => {
    switch (provider) {
      case 'kakao':
        return <span style={{ fontSize: '0.75rem', color: '#eab308', fontWeight: '600' }}>💬 카카오 연동됨</span>;
      case 'google':
        return <span style={{ fontSize: '0.75rem', color: '#2563eb', fontWeight: '600' }}>🌐 구글 연동됨</span>;
      case 'both':
        return <span style={{ fontSize: '0.75rem', color: '#16a34a', fontWeight: '600' }}>💬 카카오, 🌐 구글 연동됨</span>;
      case 'none':
      default:
        return <span style={{ fontSize: '0.75rem', color: '#999999' }}>(일반 이메일 계정)</span>;
    }
  };

  // 프로필 정보 저장
  const handleSaveProfile = () => {
    localStorage.setItem('user_name', userName);
    localStorage.setItem('user_phone', userPhone);
    alert('프로필 정보가 성공적으로 저장되었습니다.');
    if (onNavigate) onNavigate('mypage');
  };

  // 비밀번호 변경 처리
  const handleChangePassword = (e) => {
    e.preventDefault();
    if (!currentPassword || !newPassword || !confirmPassword) {
      alert('모든 비밀번호 입력 항목을 채워주세요.');
      return;
    }
    if (newPassword !== confirmPassword) {
      alert('새 비밀번호가 서로 일치하지 않습니다.');
      return;
    }
    alert('비밀번호가 성공적으로 변경되었습니다.');
    setIsChangingPassword(false);
    setCurrentPassword('');
    setNewPassword('');
    setConfirmPassword('');
  };

  // 6. 회원 탈퇴 처리
  const handleDeleteAccount = () => {
    const confirmed = window.confirm(
      '정말로 탈퇴하시겠습니까?\n탈퇴 시 모든 데이터 및 분석 기록이 삭제되며 복구할 수 없습니다.'
    );
    if (confirmed) {
      alert('회원 탈퇴가 완료되었습니다. 그동안 이용해주셔서 감사합니다.');
      localStorage.clear(); // 데이터 초기화
      if (onNavigate) onNavigate('login');
    }
  };

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
          <h1>내 정보 관리</h1>
          <span className="mypage-top-space" />
        </div>

        <div className="profile-container" style={{ marginTop: '20px', paddingBottom: '30px' }}>
          
          {/* 1. 프로필 아바타 이미지 */}
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', marginBottom: '24px' }}>
            <div style={{
              width: '80px',
              height: '80px',
              borderRadius: '50%',
              backgroundColor: '#2563eb',
              color: '#ffffff',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              fontSize: '1.8rem',
              fontWeight: 'bold',
              marginBottom: '8px'
            }}>
              {userName ? userName.charAt(0) : 'U'}
            </div>
            <span style={{ fontSize: '0.85rem', color: '#666' }}>프로필 아바타</span>
          </div>

          {/* 폼 영역 */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '18px' }}>
            
            {/* 이름(닉네임) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.875rem', fontWeight: '600', color: '#333' }}>이름</label>
              <input 
                type="text" 
                value={userName} 
                onChange={(e) => setUserName(e.target.value)}
                placeholder="이름을 입력하세요"
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  fontSize: '0.95rem',
                  outline: 'none'
                }}
              />
            </div>

            {/* 2. 이메일 계정 (표시용 - 상태에 따른 동적 연동 표시) */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <label style={{ fontSize: '0.875rem', fontWeight: '600', color: '#777' }}>이메일 계정</label>
                {/* 조건에 따른 동적 표시 영역 */}
                {renderSocialStatus()}
              </div>
              <input 
                type="email" 
                value={userEmail} 
                disabled 
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid #eee',
                  backgroundColor: '#f5f5f5',
                  color: '#777',
                  fontSize: '0.95rem',
                  cursor: 'not-allowed'
                }}
              />
            </div>

            {/* 3. 전화번호 */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label style={{ fontSize: '0.875rem', fontWeight: '600', color: '#333' }}>전화번호</label>
              <input 
                type="tel" 
                value={userPhone} 
                onChange={(e) => setUserPhone(e.target.value)}
                placeholder="010-0000-0000"
                style={{
                  padding: '12px',
                  borderRadius: '8px',
                  border: '1px solid #ddd',
                  fontSize: '0.95rem',
                  outline: 'none'
                }}
              />
            </div>

            {/* 4. 비밀번호 변경 버튼 및 레이어 */}
            <div style={{ borderTop: '1px solid #f0f0f0', paddingTop: '16px', marginTop: '6px' }}>
              {!isChangingPassword ? (
                <button
                  type="button"
                  onClick={() => setIsChangingPassword(true)}
                  style={{
                    width: '100%',
                    padding: '12px',
                    backgroundColor: '#f8fafc',
                    color: '#334155',
                    border: '1px solid #cbd5e1',
                    borderRadius: '8px',
                    fontWeight: '600',
                    fontSize: '0.9rem',
                    cursor: 'pointer'
                  }}
                >
                  🔒 비밀번호 변경하기
                </button>
              ) : (
                <form onSubmit={handleChangePassword} style={{ display: 'flex', flexDirection: 'column', gap: '10px', backgroundColor: '#f8fafc', padding: '14px', borderRadius: '8px', border: '1px solid #e2e8f0' }}>
                  <div style={{ fontWeight: '600', fontSize: '0.9rem', color: '#1e293b' }}>비밀번호 변경</div>
                  <input 
                    type="password" 
                    placeholder="현재 비밀번호" 
                    value={currentPassword}
                    onChange={(e) => setCurrentPassword(e.target.value)}
                    style={{ padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.875rem' }}
                  />
                  <input 
                    type="password" 
                    placeholder="새 비밀번호" 
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    style={{ padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.875rem' }}
                  />
                  <input 
                    type="password" 
                    placeholder="새 비밀번호 확인" 
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    style={{ padding: '10px', borderRadius: '6px', border: '1px solid #cbd5e1', fontSize: '0.875rem' }}
                  />
                  <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                    <button 
                      type="submit" 
                      style={{ flex: 1, padding: '8px', backgroundColor: '#2563eb', color: '#fff', border: 'none', borderRadius: '6px', fontWeight: '600', fontSize: '0.85rem', cursor: 'pointer' }}
                    >
                      변경 확정
                    </button>
                    <button 
                      type="button" 
                      onClick={() => setIsChangingPassword(false)}
                      style={{ flex: 1, padding: '8px', backgroundColor: '#e2e8f0', color: '#475569', border: 'none', borderRadius: '6px', fontWeight: '600', fontSize: '0.85rem', cursor: 'pointer' }}
                    >
                      취소
                    </button>
                  </div>
                </form>
              )}
            </div>

            {/* 저장하기 버튼 */}
            <button 
              type="button"
              onClick={handleSaveProfile}
              style={{
                marginTop: '10px',
                padding: '14px',
                backgroundColor: '#2563eb',
                color: '#ffffff',
                border: 'none',
                borderRadius: '8px',
                fontWeight: '600',
                fontSize: '1rem',
                cursor: 'pointer'
              }}
            >
              저장하기
            </button>

            {/* 5. 회원 탈퇴 (하단 소형 텍스트) */}
            <div style={{ textAlign: 'center', marginTop: '24px' }}>
              <button 
                type="button"
                onClick={handleDeleteAccount}
                style={{
                  background: 'none',
                  border: 'none',
                  color: '#94a3b8',
                  fontSize: '0.8rem',
                  textDecoration: 'underline',
                  cursor: 'pointer'
                }}
              >
                회원 탈퇴
              </button>
            </div>

          </div>
        </div>
      </div>
    </section>
  );
}

export default EditProfilePage;