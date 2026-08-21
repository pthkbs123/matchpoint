import { useEffect, useRef, useState } from 'react';
import { apiFetch } from '../api';

const HIGH_QUALITY_VIDEO_CONSTRAINTS = {
  width: { ideal: 1920 },
  height: { ideal: 1080 },
  frameRate: { ideal: 30 },
  resizeMode: 'none',
};

const STABILIZATION_FRAME_COUNT = 5;
const STABILIZATION_INTERVAL_MS = 55;

const wait = (milliseconds) => new Promise((resolve) => setTimeout(resolve, milliseconds));

function createTrackConstraints(advanced) {
  return {
    ...HIGH_QUALITY_VIDEO_CONSTRAINTS,
    ...(advanced ? { advanced: [advanced] } : {}),
  };
}

function CameraPage({ onNavigate, onBack, onCapture, token, selectedChildId }) {
  const videoRef = useRef(null);
  const streamRef = useRef(null);
  const fileInputRef = useRef(null);
  const capabilitiesRef = useRef({});
  const focusTargetRef = useRef(null);
  const focusTimerRef = useRef(null);
  const [error, setError] = useState(null);
  const [childName, setChildName] = useState('');
  const [facingMode, setFacingMode] = useState('environment');
  const [torchSupported, setTorchSupported] = useState(false);
  const [torchEnabled, setTorchEnabled] = useState(false);
  const [tapFocusSupported, setTapFocusSupported] = useState(false);
  const [focusIndicator, setFocusIndicator] = useState(null);
  const [cameraNotice, setCameraNotice] = useState('');
  const [cameraQuality, setCameraQuality] = useState('');
  const [isCapturing, setIsCapturing] = useState(false);

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

    setError(null);
    setCameraNotice('');
    setTorchSupported(false);
    setTorchEnabled(false);
    setTapFocusSupported(false);
    setFocusIndicator(null);
    setCameraQuality('');
    capabilitiesRef.current = {};
    focusTargetRef.current = null;

    getUserMedia.call(navigator.mediaDevices, {
      video: {
        facingMode: { ideal: facingMode },
        ...HIGH_QUALITY_VIDEO_CONSTRAINTS,
      },
      audio: false,
    })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) videoRef.current.srcObject = stream;

        const videoTrack = stream.getVideoTracks()[0];
        const capabilities = videoTrack?.getCapabilities?.() || {};
        const supportedConstraints = navigator.mediaDevices.getSupportedConstraints?.() || {};
        const focusModes = Array.isArray(capabilities.focusMode) ? capabilities.focusMode : [];
        const supportsTapFocus = supportedConstraints.pointsOfInterest === true
          && (focusModes.includes('single-shot') || focusModes.includes('continuous'));
        const settings = videoTrack?.getSettings?.() || {};
        const longestSide = Math.max(settings.width || 0, settings.height || 0);

        const supportsTorch = capabilities.torch === true
          || (Array.isArray(capabilities.torch) && capabilities.torch.includes(true));

        capabilitiesRef.current = capabilities;
        setTorchSupported(supportsTorch);
        setTapFocusSupported(supportsTapFocus);
        setCameraQuality(longestSide >= 1920 ? 'FHD' : longestSide >= 1280 ? 'HD' : longestSide ? `${settings.width}×${settings.height}` : '');

        if (focusModes.includes('continuous')) {
          videoTrack.applyConstraints(createTrackConstraints({ focusMode: 'continuous' })).catch(() => {});
        }
      })
      .catch(() => {
        if (!cancelled) setError('카메라를 사용할 수 없어요. 브라우저 권한을 확인해주세요.');
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
      clearTimeout(focusTimerRef.current);
    };
  }, [facingMode]);

  const handleSwitchCamera = () => {
    setFacingMode((current) => (current === 'environment' ? 'user' : 'environment'));
  };

  const handleTorchToggle = async () => {
    const videoTrack = streamRef.current?.getVideoTracks()[0];
    if (!videoTrack || !torchSupported) return;

    const nextTorchState = !torchEnabled;
    try {
      const advanced = { torch: nextTorchState };
      const focusModes = capabilitiesRef.current.focusMode || [];
      if (focusTargetRef.current && tapFocusSupported) {
        advanced.pointsOfInterest = [focusTargetRef.current];
        advanced.focusMode = focusModes.includes('single-shot') ? 'single-shot' : 'continuous';
      }
      await videoTrack.applyConstraints(createTrackConstraints(advanced));
      setTorchEnabled(nextTorchState);
      setCameraNotice(nextTorchState ? '플래시를 켰어요' : '플래시를 껐어요');
    } catch {
      setTorchSupported(false);
      setTorchEnabled(false);
      setCameraNotice('이 기기에서는 플래시를 제어할 수 없어요');
    }
  };

  const handleTapToFocus = async (event) => {
    if (event.target.closest?.('button') || error) return;

    const video = videoRef.current;
    const videoTrack = streamRef.current?.getVideoTracks()[0];
    if (!video || !videoTrack || !video.videoWidth || !video.videoHeight) return;

    const rect = video.getBoundingClientRect();
    const visualX = Math.min(Math.max(event.clientX - rect.left, 0), rect.width);
    const visualY = Math.min(Math.max(event.clientY - rect.top, 0), rect.height);
    const videoAspectRatio = video.videoWidth / video.videoHeight;
    const viewAspectRatio = rect.width / rect.height;
    let normalizedX;
    let normalizedY;

    if (videoAspectRatio > viewAspectRatio) {
      const renderedWidth = rect.width;
      const renderedHeight = renderedWidth / videoAspectRatio;
      const offsetY = (rect.height - renderedHeight) / 2;
      if (visualY < offsetY || visualY > offsetY + renderedHeight) return;
      normalizedX = visualX / renderedWidth;
      normalizedY = (visualY - offsetY) / renderedHeight;
    } else {
      const renderedHeight = rect.height;
      const renderedWidth = renderedHeight * videoAspectRatio;
      const offsetX = (rect.width - renderedWidth) / 2;
      if (visualX < offsetX || visualX > offsetX + renderedWidth) return;
      normalizedX = (visualX - offsetX) / renderedWidth;
      normalizedY = visualY / renderedHeight;
    }

    if (facingMode === 'user') normalizedX = 1 - normalizedX;
    const focusTarget = {
      x: Math.min(Math.max(normalizedX, 0), 1),
      y: Math.min(Math.max(normalizedY, 0), 1),
    };

    clearTimeout(focusTimerRef.current);
    setFocusIndicator({ x: visualX, y: visualY, status: 'focusing' });

    if (!tapFocusSupported) {
      setCameraNotice('이 기기에서는 터치 초점 대신 자동 초점을 사용해요');
      setFocusIndicator({ x: visualX, y: visualY, status: 'unsupported' });
      focusTimerRef.current = setTimeout(() => setFocusIndicator(null), 1400);
      return;
    }

    const focusModes = capabilitiesRef.current.focusMode || [];
    const advanced = {
      pointsOfInterest: [focusTarget],
      focusMode: focusModes.includes('single-shot') ? 'single-shot' : 'continuous',
    };
    if (torchSupported) advanced.torch = torchEnabled;

    try {
      await videoTrack.applyConstraints(createTrackConstraints(advanced));
      focusTargetRef.current = focusTarget;
      setFocusIndicator({ x: visualX, y: visualY, status: 'focused' });
      setCameraNotice('선택한 위치에 초점을 맞췄어요');
    } catch {
      setTapFocusSupported(false);
      setFocusIndicator({ x: visualX, y: visualY, status: 'unsupported' });
      setCameraNotice('터치 초점을 적용하지 못해 자동 초점으로 전환했어요');
      if (focusModes.includes('continuous')) {
        videoTrack.applyConstraints(createTrackConstraints({ focusMode: 'continuous' })).catch(() => {});
      }
    }

    focusTimerRef.current = setTimeout(() => setFocusIndicator(null), 1400);
  };

  const createVideoFrameCanvas = () => {
    const video = videoRef.current;
    if (!video || !video.videoWidth) {
      return null;
    }

    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const context = canvas.getContext('2d');
    if (!context) {
      return null;
    }
    context.imageSmoothingEnabled = true;
    context.imageSmoothingQuality = 'high';
    if (facingMode === 'user') {
      context.translate(canvas.width, 0);
      context.scale(-1, 1);
      context.drawImage(video, 0, 0);
    } else {
      context.drawImage(video, 0, 0);
    }

    return canvas;
  };

  const calculateSharpness = (sourceCanvas) => {
    const sampleCanvas = document.createElement('canvas');
    const sampleWidth = 180;
    const sampleHeight = Math.max(1, Math.round(sampleWidth * sourceCanvas.height / sourceCanvas.width));
    sampleCanvas.width = sampleWidth;
    sampleCanvas.height = sampleHeight;
    const context = sampleCanvas.getContext('2d', { willReadFrequently: true });
    if (!context) return 0;
    context.drawImage(sourceCanvas, 0, 0, sampleWidth, sampleHeight);

    const { data } = context.getImageData(0, 0, sampleWidth, sampleHeight);
    const luminance = (index) => data[index] * 0.299 + data[index + 1] * 0.587 + data[index + 2] * 0.114;
    let sum = 0;
    let squaredSum = 0;
    let count = 0;

    for (let y = 1; y < sampleHeight - 1; y += 1) {
      for (let x = 1; x < sampleWidth - 1; x += 1) {
        const center = (y * sampleWidth + x) * 4;
        const laplacian = 4 * luminance(center)
          - luminance(center - 4)
          - luminance(center + 4)
          - luminance(center - sampleWidth * 4)
          - luminance(center + sampleWidth * 4);
        sum += laplacian;
        squaredSum += laplacian * laplacian;
        count += 1;
      }
    }

    if (!count) return 0;
    const average = sum / count;
    return squaredSum / count - average * average;
  };

  const captureStabilizedFrame = async () => {
    let sharpestCanvas = null;
    let highestSharpness = -1;

    for (let index = 0; index < STABILIZATION_FRAME_COUNT; index += 1) {
      const canvas = createVideoFrameCanvas();
      if (canvas) {
        const sharpness = calculateSharpness(canvas);
        if (sharpness > highestSharpness) {
          sharpestCanvas = canvas;
          highestSharpness = sharpness;
        }
      }
      if (index < STABILIZATION_FRAME_COUNT - 1) await wait(STABILIZATION_INTERVAL_MS);
    }

    if (!sharpestCanvas) return null;
    return new Promise((resolve) => sharpestCanvas.toBlob(resolve, 'image/jpeg', 0.96));
  };

  const handleShutter = async () => {
    if (isCapturing) return;
    setIsCapturing(true);
    setCameraNotice('흔들림이 적은 프레임을 고르는 중이에요...');

    const capturedBlob = await captureStabilizedFrame();

    if (capturedBlob) {
      setIsCapturing(false);
      onCapture(capturedBlob, capturedBlob);
      onNavigate('preview');
      return;
    } else {
      setCameraNotice('사진을 저장하지 못했어요. 다시 촬영해 주세요');
    }

    setIsCapturing(false);
  };

  const handleFallbackCapture = (event) => {
    const file = event.target.files?.[0];
    if (!file) return;
    onCapture(file, file);
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
      <div className={`camera-view ${tapFocusSupported ? 'tap-focus-enabled' : ''}`} onClick={handleTapToFocus}>
        <div className="camera-top">
          <button className="back-button dark-button" onClick={onBack || (() => onNavigate('home'))}>← 뒤로</button>
          <div className="camera-status-badges">
            {cameraQuality && <span className="camera-quality-badge">{cameraQuality}</span>}
            <span className="live-badge"><i /> LIVE</span>
          </div>
        </div>
        <div className="camera-subject">{childName ? `${childName} 촬영 중` : '자녀 미선택'}</div>
        {!error && <video ref={videoRef} className={`camera-feed ${facingMode === 'user' ? 'mirrored' : ''}`} autoPlay playsInline muted />}
        {focusIndicator && (
          <span
            className={`camera-focus-ring ${focusIndicator.status}`}
            style={{ left: focusIndicator.x, top: focusIndicator.y }}
            aria-hidden="true"
          />
        )}
        <p className="camera-hint">{selectedChildId == null ? '촬영 전에 자녀 프로필을 선택해 주세요' : error || cameraNotice || (tapFocusSupported ? '전체 화각을 유지하며, 화면을 눌러 초점을 맞출 수 있어요' : '보이는 전체 화각 그대로 촬영돼요')}</p>
        <div className="camera-guide" />
        <button className="camera-guide-link" onClick={() => onNavigate('care-guide')}>촬영·위생 가이드</button>
      </div>
      <div className="camera-controls">
        <button className="control-link" onClick={onBack || (() => onNavigate('home'))}>뒤로가기</button>
        <button
          type="button"
          className="camera-tool-button"
          onClick={handleSwitchCamera}
          disabled={Boolean(error)}
          aria-label={facingMode === 'environment' ? '전면 카메라로 전환' : '후면 카메라로 전환'}
        >
          <span aria-hidden="true">↻</span>
          <small>{facingMode === 'environment' ? '전면' : '후면'}</small>
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          capture={facingMode}
          onChange={handleFallbackCapture}
          hidden
        />
        <button className="shutter" onClick={handleCaptureButton} disabled={isCapturing} aria-label={error ? '사진 촬영 또는 선택' : isCapturing ? '고화질 사진 저장 중' : '촬영'} />
        <button
          type="button"
          className={`camera-tool-button ${torchEnabled ? 'active' : ''}`}
          onClick={handleTorchToggle}
          disabled={!torchSupported}
          aria-pressed={torchEnabled}
          aria-label={torchSupported ? `플래시 ${torchEnabled ? '끄기' : '켜기'}` : '플래시를 지원하지 않는 기기'}
        >
          <span aria-hidden="true">⚡</span>
          <small>{torchSupported ? (torchEnabled ? '켜짐' : '플래시') : '미지원'}</small>
        </button>
        <button className="control-link" onClick={() => onNavigate('home')}>홈</button>
      </div>
    </section>
  );
}
export default CameraPage;
