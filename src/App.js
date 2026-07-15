import { useState } from 'react';
import './App.css';
import MainPage from './pages/MainPage';
import CameraPage from './pages/CameraPage';
import CapturePreviewPage from './pages/CapturePreviewPage';
import AnalyzingPage from './pages/AnalyzingPage';
import ResultPage from './pages/ResultPage';
import ReportPage from './pages/ReportPage';

function App() {
  const [page, setPage] = useState('home');

  const pages = {
    home: <MainPage onNavigate={setPage} />,
    camera: <CameraPage onNavigate={setPage} />,
    preview: <CapturePreviewPage onNavigate={setPage} />,
    analyzing: <AnalyzingPage onNavigate={setPage} />,
    result: <ResultPage onNavigate={setPage} />,
    report: <ReportPage onNavigate={setPage} />,
  };

  return <main className="app-shell">{pages[page]}</main>;
}

export default App;
