import { useCallback, useState } from 'react';
import './App.css';
import MainPage from './pages/MainPage';
import CameraPage from './pages/CameraPage';
import CapturePreviewPage from './pages/CapturePreviewPage';
import AnalyzingPage from './pages/AnalyzingPage';
import ResultPage from './pages/ResultPage';
import ReportPage from './pages/ReportPage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';
import MyPage from './pages/MyPage';
import FindAccountPage from './pages/FindAccountPage';
import ResetPasswordPage from './pages/ResetPasswordPage';
import HistoryPage from './pages/HistoryPage';
import NotificationPage from './pages/NotificationPage';
import ProfilePage from './pages/ProfilePage';

function App() {
  const savedSession = (() => {
    const value = sessionStorage.getItem('smileguard-session') || localStorage.getItem('smileguard-session');
    try { return value ? JSON.parse(value) : null; } catch { return null; }
  })();
  const resetToken = new URLSearchParams(window.location.search).get('resetToken');
  const [session, setSession] = useState(savedSession);
  const [page, setPage] = useState(() => {
    if (resetToken) return 'reset-password';
    return savedSession ? 'home' : 'login';
  });
  const [capturedBlob, setCapturedBlob] = useState(null);
  const [capturedUrl, setCapturedUrl] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);

  const handleCapture = useCallback((blob) => {
    setCapturedUrl((prev) => {
      if (prev) URL.revokeObjectURL(prev);
      return URL.createObjectURL(blob);
    });
    setCapturedBlob(blob);
    setAnalysisResult(null);
  }, []);

  const handleLogin = ({ user, accessToken, provider, remember }) => {
    const storage = remember ? localStorage : sessionStorage;
    const nextSession = {
      user,
      accessToken,
      provider,
    };
    localStorage.removeItem('smileguard-session');
    sessionStorage.removeItem('smileguard-session');
    storage.setItem('smileguard-session', JSON.stringify(nextSession));
    setSession(nextSession);
    setPage('home');
  };

  const handleLogout = () => {
    localStorage.removeItem('smileguard-session');
    sessionStorage.removeItem('smileguard-session');
    setSession(null);
    setPage('login');
  };

  const pages = {
    login: <LoginPage onLogin={handleLogin} onNavigate={setPage} />,
    signup: <SignUpPage onNavigate={setPage} />,
    'find-id': <FindAccountPage onNavigate={setPage} initialTab="id" />,
    'find-password': <FindAccountPage onNavigate={setPage} initialTab="password" />,
    'reset-password': <ResetPasswordPage onNavigate={setPage} token={resetToken} />,
    home: <MainPage onNavigate={setPage} user={session?.user} token={session?.accessToken} />,
    mypage: <MyPage onNavigate={setPage} user={session?.user} token={session?.accessToken} onLogout={handleLogout} />,
    history: <HistoryPage onNavigate={setPage} token={session?.accessToken} />,
    notification: <NotificationPage onNavigate={setPage} />,
    profile: <ProfilePage onNavigate={setPage} />,
    camera: <CameraPage onNavigate={setPage} onCapture={handleCapture} />,
    preview: <CapturePreviewPage onNavigate={setPage} capturedUrl={capturedUrl} />,
    analyzing: (
      <AnalyzingPage
        onNavigate={setPage}
        capturedBlob={capturedBlob}
        token={session?.accessToken}
        onAnalysisComplete={setAnalysisResult}
      />
    ),
    result: <ResultPage onNavigate={setPage} analysisResult={analysisResult} capturedUrl={capturedUrl} />,
    report: <ReportPage onNavigate={setPage} />,
  };

  return <main className="app-shell">{pages[page]}</main>;
}

export default App;
