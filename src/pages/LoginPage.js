import { useState } from 'react';

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [autoLogin, setAutoLogin] = useState(
    () => localStorage.getItem('smileguard-auto-login') === 'true'
  );

  const handleSubmit = (event) => {
    event.preventDefault();
    localStorage.setItem('smileguard-auto-login', String(autoLogin));
    onLogin();
  };

  return (
    <section className="phone login-page">
      <div className="login-decoration login-decoration-one" />
      <div className="login-decoration login-decoration-two" />

      <div className="login-content">
        <div className="brand-mark" aria-hidden="true">
          <span>✓</span>
        </div>
        <p className="eyebrow">SMILEGUARD</p>
        <h1>건강한 미소를<br />매일 확인하세요</h1>
        <p className="subtext">나만의 구강 건강 기록을 시작해 보세요.</p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="input-group">
            <span>이메일</span>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="이메일을 입력해 주세요"
              autoComplete="email"
              required
            />
          </label>

          <label className="input-group">
            <span>비밀번호</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="비밀번호를 입력해 주세요"
              autoComplete="current-password"
              required
            />
          </label>

          <div className="login-options">
            <label className="check-label">
              <input
                type="checkbox"
                checked={autoLogin}
                onChange={(event) => setAutoLogin(event.target.checked)}
              />
              <span className="custom-check">✓</span>
              자동 로그인
            </label>
            <button type="button" className="text-button">비밀번호 찾기</button>
          </div>

          <button type="submit" className="login-button">로그인</button>
        </form>

        <p className="join-text">
          아직 회원이 아니신가요?
          <button type="button" className="text-button">회원가입</button>
        </p>
      </div>
    </section>
  );
}

export default LoginPage;
