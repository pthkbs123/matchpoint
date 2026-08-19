import { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../api';

function CameraPage({ onNavigate, onCapture, token, selectedChildId }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const fileInputRef = useRef(null);
  const [error, setError] = useState(null);
  const [childName, setChildName] = useState('');

  useEffect(() => {
    if (!token || selectedChildId == null) return undefined;
    let cancelled = false;
    apiFetch('/api/children', { token })
      .then((data) => {
        const child = (data.children || []).find((item) => item.id === selectedChildId);
        if (!cancelled) setChildName(child?.name || '');
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [token, selectedChildId]);

  useEffect(() => {
    let cancelled = false;

    const getUserMedia = navigator.mediaDevices?.getUserMedia;
    if (!getUserMedia) {
      setError('현재 접속 주소에서는 실시간 카메라를 사용할 수 없어요. 촬영 버튼으로 사진을 찍어주세요.');
      return undefined;
    }

    getUserMedia.call(navigator.mediaDevices, { video: { facingMode: 'environment' }, audio: false })
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

  const handleFallbackCapture = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    onCapture(file);
    onNavigate('preview');
    event.target.value = '';
  };

  const handleCaptureButton = () => {
    if (selectedChildId == null) {
      onNavigate('child-profile');
      return;
    }
    if (error) {
      fileInputRef.current?.click();
      return;
    }
    handleShutter();
  };

  return (
    <section className="phone camera-screen">
      <div className="camera-view">
        <div className="camera-top">
          <button className="back-button dark-button" onClick={() => onNavigate('home')}>← 뒤로</button>
          <span className="live-badge"><i /> LIVE</span>
        </div>
        <div className="camera-subject">{childName ? `${childName} 촬영 중` : '자녀 미선택'}</div>
        {!error && <video ref={videoRef} className="camera-feed" autoPlay playsInline muted />}
        <p className="camera-hint">{selectedChildId == null ? '촬영 전에 자녀 프로필을 선택해 주세요' : error || '치아가 가이드 안에 들어오도록 맞춰주세요'}</p>
        <div className="camera-guide" />
        <button className="camera-guide-link" onClick={() => onNavigate('care-guide')}>촬영·위생 가이드</button>
      </div>
      <div className="camera-controls">
        <button className="control-link" onClick={() => onNavigate('home')}>뒤로가기</button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture="environment"
          onChange={handleFallbackCapture}
          hidden
        />
        <button className="shutter" onClick={handleCaptureButton} aria-label={error ? '사진 촬영 또는 선택' : '촬영'} />
        <button className="control-link" onClick={() => onNavigate('home')}>홈</button>
      </div>
    </section>
  );
}
export default CameraPage;
