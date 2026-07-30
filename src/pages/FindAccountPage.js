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

function FindIdForm() {
  const [form, setForm] = useState({ name: '', email: '' });
  const [result, setResult] = useState(null);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');
    setResult(null);

    if (!form.name.trim() || !form.email.trim()) {
      setError('이름과 이메일을 모두 입력해 주세요.');
      return;
    }

    setIsSubmitting(true);
    try {
      const data = await requestApi('/api/auth/find-id', form);
      setResult(data.maskedId || data.email || '일치하는 계정을 찾았어요.');
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (result) {
    return (
      <div className="find-result">
        <p className="find-result-label">가입하신 아이디예요</p>
        <p className="find-result-value">{result}</p>
        <button type="button" className="login-button" onClick={() => setResult(null)}>
          다시 찾기
        </button>
      </div>
    );
  }

  return (
    <form className="login-form" onSubmit={handleSubmit} noValidate>
      <label className="input-group">
        <span>이름</span>
        <input name="name" type="text" value={form.name} onChange={handleChange} placeholder="가입 시 등록한 이름" autoComplete="name" />
      </label>
      <label className="input-group">
        <span>이메일</span>
        <input name="email" type="email" value={form.email} onChange={handleChange} placeholder="가입 시 등록한 이메일" autoComplete="email" />
      </label>
      {error && <p className="social-error" role="alert">{error}</p>}
      <button type="submit" className="login-button" disabled={isSubmitting}>
        {isSubmitting ? '확인 중...' : '아이디 찾기'}
      </button>
    </form>
  );
}

function FindPasswordForm() {
  const [email, setEmail] = useState('');
  const [isSent, setIsSent] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = async (event) => {
    event.preventDefault();
    setError('');

    if (!email.trim()) {
      setError('이메일을 입력해 주세요.');
      return;
    }

    setIsSubmitting(true);
    try {
      await requestApi('/api/auth/reset-password/request', { email });
      setIsSent(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isSent) {
    return (
      <div className="find-result">
        <p className="find-result-label">메일함을 확인해 주세요</p>
        <p className="find-result-value" style={{ fontSize: 15 }}>
          {email}(으)로<br />비밀번호 재설정 링크를 보냈어요.
        </p>
        <button type="button" className="login-button" onClick={() => setIsSent(false)}>
          다시 보내기
        </button>
      </div>
    );
  }

  return (
    <form className="login-form" onSubmit={handleSubmit} noValidate>
      <label className="input-group">
        <span>이메일</span>
        <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="가입 시 등록한 이메일" autoComplete="email" />
      </label>
      {error && <p className="social-error" role="alert">{error}</p>}
      <button type="submit" className="login-button" disabled={isSubmitting}>
        {isSubmitting ? '전송 중...' : '재설정 링크 받기'}
      </button>
    </form>
  );
}

function FindAccountPage({ onNavigate, initialTab = 'id' }) {
  const [tab, setTab] = useState(initialTab);

  return (
    <section className="phone login-page">
      <div className="login-decoration login-decoration-one" />
      <div className="login-decoration login-decoration-two" />

      <div className="login-content">
        <button type="button" className="back-button" style={{ marginBottom: 18 }} onClick={() => onNavigate('login')}>
          ← 로그인으로
        </button>
        <p className="eyebrow">SMILEGUARD</p>
        <h1>계정 정보를<br />찾아드릴게요</h1>
        <p className="subtext">가입 시 입력한 정보로 아이디 또는 비밀번호를 확인하세요.</p>

        <div className="tab-group" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'id'}
            className={`tab-button ${tab === 'id' ? 'active' : ''}`}
            onClick={() => setTab('id')}
          >
            아이디 찾기
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === 'password'}
            className={`tab-button ${tab === 'password' ? 'active' : ''}`}
            onClick={() => setTab('password')}
          >
            비밀번호 찾기
          </button>
        </div>

        {tab === 'id' ? <FindIdForm /> : <FindPasswordForm />}
      </div>
    </section>
  );
}

export default FindAccountPage;