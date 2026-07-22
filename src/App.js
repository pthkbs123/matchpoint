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
  const [page, setPage] = useState('login');

  const pages = {
    login: <LoginPage onLogin={() => setPage('home')} />,
    home: <MainPage onNavigate={setPage} />,
    mypage: <MyPage onNavigate={setPage} />,
    camera: <CameraPage onNavigate={setPage} />,
    preview: <CapturePreviewPage onNavigate={setPage} />,
    analyzing: <AnalyzingPage onNavigate={setPage} />,
    result: <ResultPage onNavigate={setPage} />,
    report: <ReportPage onNavigate={setPage} />,
  };

  return <main className="app-shell">{pages[page]}</main>;
}

export default App;
