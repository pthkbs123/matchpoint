import { useCallback, useEffect, useRef, useState } from 'react';

const GOOGLE_SCRIPT_URL = 'https://accounts.google.com/gsi/client';
const KAKAO_SCRIPT_URL = 'https://t1.kakaocdn.net/kakao_js_sdk/2.8.1/kakao.min.js';
const API_BASE_URL = (process.env.REACT_APP_API_BASE_URL || '').replace(/\/$/, '');
const GOOGLE_CLIENT_ID = process.env.REACT_APP_GOOGLE_CLIENT_ID;
const KAKAO_JAVASCRIPT_KEY = process.env.REACT_APP_KAKAO_JAVASCRIPT_KEY;
const KAKAO_REDIRECT_URI = process.env.REACT_APP_KAKAO_REDIRECT_URI || `${window.location.origin}/`;

function loadScript(id, src) {
  return new Promise((resolve, reject) => {
    const existing = document.getElementById(id);
    if (existing) {
      if (existing.dataset.loaded === 'true') resolve();
      else existing.addEventListener('load', resolve, { once: true });
      return;
    }

    const script = document.createElement('script');
    script.id = id;
    script.src = src;
    script.async = true;
    script.defer = true;
    script.onload = () => {
      script.dataset.loaded = 'true';
      resolve();
    };
    script.onerror = () => reject(new Error('로그인 SDK를 불러오지 못했습니다.'));
    document.head.appendChild(script);
  });
}

async function requestSocialLogin(path, payload) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.message || '소셜 로그인 처리에 실패했습니다.');
  }

  return response.json();
}

function LoginPage({ onLogin }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [autoLogin, setAutoLogin] = useState(
    () => localStorage.getItem('smileguard-auto-login') === 'true'
  );
  const [socialError, setSocialError] = useState('');
  const [isSocialLoading, setIsSocialLoading] = useState(false);
  const googleButtonRef = useRef(null);

  const completeSocialLogin = useCallback((data, provider) => {
    onLogin({
      user: data.user,
      accessToken: data.accessToken,
      provider,
      remember: autoLogin,
    });
  }, [autoLogin, onLogin]);

  const handleGoogleCredential = useCallback(async (response) => {
    setSocialError('');
    setIsSocialLoading(true);

    try {
      const data = await requestSocialLogin('/api/auth/google', {
        credential: response.credential,
      });
      completeSocialLogin(data, 'google');
    } catch (error) {
      setSocialError(error.message);
    } finally {
      setIsSocialLoading(false);
    }
  }, [completeSocialLogin]);

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID || !googleButtonRef.current) return undefined;
    let cancelled = false;

    loadScript('google-identity-service', GOOGLE_SCRIPT_URL)
      .then(() => {
        if (cancelled || !window.google || !googleButtonRef.current) return;
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleGoogleCredential,
        });
        googleButtonRef.current.innerHTML = '';
        window.google.accounts.id.renderButton(googleButtonRef.current, {
          type: 'standard',
          theme: 'outline',
          size: 'large',
          text: 'continue_with',
          shape: 'rectangular',
          logo_alignment: 'left',
          width: 340,
          locale: 'ko',
        });
      })
      .catch((error) => setSocialError(error.message));

    return () => { cancelled = true; };
  }, [handleGoogleCredential]);

  useEffect(() => {
    if (!KAKAO_JAVASCRIPT_KEY) return undefined;
    loadScript('kakao-javascript-sdk', KAKAO_SCRIPT_URL)
      .then(() => {
        if (window.Kakao && !window.Kakao.isInitialized()) {
          window.Kakao.init(KAKAO_JAVASCRIPT_KEY);
        }
      })
      .catch((error) => setSocialError(error.message));
    return undefined;
  }, []);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const error = params.get('error');
    const returnedState = params.get('state');
    const expectedState = sessionStorage.getItem('smileguard-kakao-state');

    if (error) {
      setSocialError(params.get('error_description') || '카카오 로그인이 취소되었습니다.');
      window.history.replaceState({}, document.title, window.location.pathname);
      return;
    }
    if (!code) return;
    if (!expectedState || expectedState !== returnedState) {
      setSocialError('카카오 로그인 요청을 확인할 수 없습니다. 다시 시도해 주세요.');
      window.history.replaceState({}, document.title, window.location.pathname);
      return;
    }

    setIsSocialLoading(true);
    requestSocialLogin('/api/auth/kakao', {
      code,
      redirectUri: KAKAO_REDIRECT_URI,
    })
      .then((data) => {
        sessionStorage.removeItem('smileguard-kakao-state');
        completeSocialLogin(data, 'kakao');
      })
      .catch((loginError) => setSocialError(loginError.message))
      .finally(() => {
        window.history.replaceState({}, document.title, window.location.pathname);
        setIsSocialLoading(false);
      });
  }, [completeSocialLogin]);

  const handleSubmit = (event) => {
    event.preventDefault();
    localStorage.setItem('smileguard-auto-login', String(autoLogin));
    onLogin({
      user: { name: '한이음', email, picture: '/profile-avatar.svg' },
      provider: 'email',
      remember: autoLogin,
    });
  };

  const handleKakaoLogin = () => {
    setSocialError('');
    if (!KAKAO_JAVASCRIPT_KEY) {
      setSocialError('카카오 JavaScript 키가 설정되지 않았습니다.');
      return;
    }
    if (!window.Kakao?.isInitialized()) {
      setSocialError('카카오 로그인 SDK를 불러오는 중입니다. 잠시 후 다시 시도해 주세요.');
      return;
    }

    const state = window.crypto.randomUUID();
    sessionStorage.setItem('smileguard-kakao-state', state);
    window.Kakao.Auth.authorize({
      redirectUri: KAKAO_REDIRECT_URI,
      state,
      scope: 'profile_nickname,profile_image,account_email',
    });
  };

  return (
    <section className="phone login-page">
      <div className="login-decoration login-decoration-one" />
      <div className="login-decoration login-decoration-two" />

      <div className="login-content">
        <div className="brand-mark" aria-hidden="true"><span>✓</span></div>
        <p className="eyebrow">SMILEGUARD</p>
        <h1>건강한 미소를<br />매일 확인하세요</h1>
        <p className="subtext">나만의 구강 건강 기록을 시작해 보세요.</p>

        <form className="login-form" onSubmit={handleSubmit}>
          <label className="input-group">
            <span>이메일</span>
            <input type="email" value={email} onChange={(event) => setEmail(event.target.value)} placeholder="이메일을 입력해 주세요" autoComplete="email" required />
          </label>
          <label className="input-group">
            <span>비밀번호</span>
            <input type="password" value={password} onChange={(event) => setPassword(event.target.value)} placeholder="비밀번호를 입력해 주세요" autoComplete="current-password" required />
          </label>
          <div className="login-options">
            <label className="check-label">
              <input type="checkbox" checked={autoLogin} onChange={(event) => setAutoLogin(event.target.checked)} />
              <span className="custom-check">✓</span>자동 로그인
            </label>
            <button type="button" className="text-button">비밀번호 찾기</button>
          </div>
          <button type="submit" className="login-button">로그인</button>
        </form>

        <div className="social-divider"><span>또는 간편 로그인</span></div>
        <div className="social-login-list" aria-busy={isSocialLoading}>
          <button type="button" className="social-button kakao-button" onClick={handleKakaoLogin} disabled={isSocialLoading}>
            <span className="kakao-symbol" aria-hidden="true">●</span>
            카카오로 계속하기
          </button>
          {GOOGLE_CLIENT_ID ? (
            <div className="google-button-wrap" ref={googleButtonRef} />
          ) : (
            <button type="button" className="social-button google-placeholder" onClick={() => setSocialError('Google 클라이언트 ID가 설정되지 않았습니다.')}>
              <span className="google-symbol" aria-hidden="true">G</span>
              Google로 계속하기
            </button>
          )}
        </div>

        {isSocialLoading && <p className="social-status">계정 정보를 확인하고 있어요...</p>}
        {socialError && <p className="social-error" role="alert">{socialError}</p>}

        <p className="join-text">아직 회원이 아니신가요?<button type="button" className="text-button">회원가입</button></p>
      </div>
    </section>
  );
}

export default LoginPage;
