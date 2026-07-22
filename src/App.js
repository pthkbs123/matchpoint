import { useState } from 'react';
import './App.css';
import MainPage from './pages/MainPage';
import CameraPage from './pages/CameraPage';
import CapturePreviewPage from './pages/CapturePreviewPage';
import AnalyzingPage from './pages/AnalyzingPage';
import ResultPage from './pages/ResultPage';
import ReportPage from './pages/ReportPage';
import LoginPage from './pages/LoginPage';
import MyPage from './pages/MyPage';

function App() {
  const savedSession = (() => {
    const value = sessionStorage.getItem('smileguard-session') || localStorage.getItem('smileguard-session');
    try { return value ? JSON.parse(value) : null; } catch { return null; }
  })();
  const [session, setSession] = useState(savedSession);
  const [page, setPage] = useState(() => {
    return savedSession ? 'home' : 'login';
  });

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
    login: <LoginPage onLogin={handleLogin} />,
    home: <MainPage onNavigate={setPage} user={session?.user} />,
    mypage: <MyPage onNavigate={setPage} user={session?.user} onLogout={handleLogout} />,
    camera: <CameraPage onNavigate={setPage} />,
    preview: <CapturePreviewPage onNavigate={setPage} />,
    analyzing: <AnalyzingPage onNavigate={setPage} />,
    result: <ResultPage onNavigate={setPage} />,
    report: <ReportPage onNavigate={setPage} />,
  };

  return <main className="app-shell">{pages[page]}</main>;
}

export default App;
