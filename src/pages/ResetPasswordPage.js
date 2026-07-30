import { useState } from 'react';

const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || '').replace(/\/$/, '');

async function requestApi(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || data.message || '요청 처리에 실패했습니다.');
  }

  return response.json();
}

function validate(password, confirmPassword) {
  const errors = {};

  if (!password) {
    errors.password = '새 비밀번호를 입력해 주세요.';
  } else if (password.length < 8) {
    errors.password = '비밀번호는 8자 이상이어야 해요.';
  }

  if (confirmPassword !== password) {
    errors.confirmPassword = '비밀번호가 일치하지 않아요.';
  }

  return errors;
}

function ResetPasswordPage({ onNavigate, token }) {
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [errors, setErrors] = useState({});
  const [serverError, setServerError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDone, setIsDone] = useState(false);

  if (!token) {
    return (
      <section className="phone login-page">
        <div className="login-decoration login-decoration-one" />
        <div className="login-decoration login-decoration-two" />
        <div className="login-content">
          <p className="eyebrow">SMILEGUARD</p>
          <h1>유효하지 않은 링크예요</h1>
          <p className="subtext">비밀번호 재설정 메일에 있는 링크를 다시 확인해 주세요.</p>
          <button
            type="button"
            className="login-button"
            style={{ marginTop: 30 }}
            onClick={() => onNavigate('find-password')}
          >
            재설정 링크 다시 받기
          </button>
        </div>
      </section>
    );
  }

  if (isDone) {
    return (
      <section className="phone login-page">
        <div className="login-decoration login-decoration-one" />
        <div className="login-decoration login-decoration-two" />
        <div className="login-content">
          <div className="brand-mark" aria-hidden="true"><span>✓</span></div>
          <p className="eyebrow">SMILEGUARD</p>
          <h1>비밀번호가 변경됐어요</h1>
          <p className="subtext">새 비밀번호로 다시 로그인해 주세요.</p>
          <button
            type="button"
            className="login-button"
            style={{ marginTop: 30 }}
            onClick={() => onNavigate('login')}
          >
            로그인하러 가기
          </button>
        </div>
      </section>
    );
  }

  const handleSubmit = async (event) => {
    event.preventDefault();
    const nextErrors = validate(password, confirmPassword);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    setServerError('');
    setIsSubmitting(true);
    try {
      await requestApi('/api/auth/reset-password/confirm', { token, password });
      setIsDone(true);
    } catch (error) {
      setServerError(error.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <section className="phone login-page">
      <div className="login-decoration login-decoration-one" />
      <div className="login-decoration login-decoration-two" />

      <div className="login-content">
        <p className="eyebrow">SMILEGUARD</p>
        <h1>새 비밀번호를<br />설정해 주세요</h1>
        <p className="subtext">로그인에 사용할 새 비밀번호를 입력해 주세요.</p>

        <form className="login-form" onSubmit={handleSubmit} noValidate>
          <label className="input-group">
            <span>새 비밀번호</span>
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="8자 이상 입력해 주세요"
              autoComplete="new-password"
            />
            {errors.password && <p className="social-error" role="alert">{errors.password}</p>}
          </label>
          <label className="input-group">
            <span>비밀번호 확인</span>
            <input
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              placeholder="비밀번호를 다시 입력해 주세요"
              autoComplete="new-password"
            />
            {errors.confirmPassword && <p className="social-error" role="alert">{errors.confirmPassword}</p>}
          </label>
          <button type="submit" className="login-button" disabled={isSubmitting}>
            {isSubmitting ? '변경 중...' : '비밀번호 변경'}
          </button>
        </form>

        {serverError && <p className="social-error" role="alert">{serverError}</p>}
      </div>
    </section>
  );
}

export default ResetPasswordPage;
