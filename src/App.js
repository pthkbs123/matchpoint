import { useCallback, useState } from 'react';
import './App.css';
import MainPage from './pages/MainPage';
import CameraPage from './pages/CameraPage';
import CapturePreviewPage from './pages/CapturePreviewPage';
import AnalyzingPage from './pages/AnalyzingPage';
import ResultPage from './pages/ResultPage';
import ReportPage from './pages/ReportPage';

function App() {
  const [page, setPage] = useState('home');
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

  const pages = {
    home: <MainPage onNavigate={setPage} />,
    camera: <CameraPage onNavigate={setPage} onCapture={handleCapture} />,
    preview: <CapturePreviewPage onNavigate={setPage} capturedUrl={capturedUrl} />,
    analyzing: (
      <AnalyzingPage
        onNavigate={setPage}
        capturedBlob={capturedBlob}
        onAnalysisComplete={setAnalysisResult}
      />
    ),
    result: <ResultPage onNavigate={setPage} analysisResult={analysisResult} capturedUrl={capturedUrl} />,
    report: <ReportPage onNavigate={setPage} />,
  };

  return <main className="app-shell">{pages[page]}</main>;
}

export default App;
