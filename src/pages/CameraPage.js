import { useEffect, useRef, useState } from 'react';

function CameraPage({ onNavigate, onCapture }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: 'environment' }, audio: false })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;
      })
      .catch(() => {
        if (!cancelled) setError('카메라를 사용할 수 없어요. 브라우저 권한을 확인해주세요.');
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((track) => track.stop());
    };
  }, []);

  const handleShutter = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) return;

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext('2d').drawImage(video, 0, 0);

    canvas.toBlob(
      (blob) => {
        if (!blob) return;
        onCapture(blob);
        onNavigate('preview');
      },
      'image/jpeg',
      0.92
    );
  };

  return (
    <section className="phone camera-screen">
      <div className="camera-view">
        <div className="camera-top">
          <button className="back-button dark-button" onClick={() => onNavigate('home')}>← 뒤로</button>
          <span>LIVE</span>
        </div>
        {!error && <video ref={videoRef} className="camera-feed" autoPlay playsInline muted />}
        <p className="camera-hint">{error || '치아가 가이드 안에 들어오도록 맞춰주세요'}</p>
        <div className="camera-guide" />
      </div>
      <div className="camera-controls">
        <button className="control-link" onClick={() => onNavigate('home')}>뒤로가기</button>
        <button className="shutter" onClick={handleShutter} disabled={!!error} aria-label="촬영" />
        <button className="control-link" onClick={() => onNavigate('home')}>홈</button>
      </div>
    </section>
  );
}
export default CameraPage;
