import { useEffect, useState } from 'react';
import { apiFetch } from '../api';
import { getCaptureSchedule } from '../captureSchedule';

function formatKoreanDate(isoDate) {
  if (!isoDate) return '';
  const [year, month, day] = isoDate.split('-').map(Number);
  if (!year || !month || !day) return '';
  return `${month}월 ${day}일`;
}

function PreCapturePage({ onNavigate, onBack, token, selectedChildId }) {
  const [child, setChild] = useState(null);
  const [summary, setSummary] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!token || selectedChildId == null) {
      setIsLoading(false);
      return undefined;
    }

    let cancelled = false;
    const query = `?child_id=${selectedChildId}`;
    Promise.all([
      apiFetch('/api/children', { token }),
      apiFetch(`/api/report/summary${query}`, { token }),
    ])
      .then(([childData, summaryData]) => {
        if (cancelled) return;
        setChild((childData.children || []).find((item) => item.id === selectedChildId) || null);
        setSummary(summaryData);
      })
      .catch(() => {})
      .finally(() => { if (!cancelled) setIsLoading(false); });

    return () => { cancelled = true; };
  }, [token, selectedChildId]);

  const schedule = getCaptureSchedule(child?.birthDate, child?.reminderWeekday);
  const scheduleLabel = summary?.notification_schedule_label || schedule.scheduleLabel;
  const dueCopy = summary?.scan_due
    ? summary?.latest_scan_date
      ? summary?.scan_overdue
        ? '권장 촬영일이 지났어요. 오늘 상태를 기록해 주세요.'
        : '권장 촬영 시기가 되었어요.'
      : '첫 촬영으로 기준 기록을 만들어 주세요.'
    : `다음 권장 촬영일은 ${formatKoreanDate(summary?.next_scan_date)}이에요.`;

  return (
    <section className="phone">
      <div className="mypage-content pre-capture-content">
        <div className="mypage-top">
          <button className="back-button" onClick={onBack || (() => onNavigate('home'))}>← 뒤로</button>
          <h1>촬영 전 확인</h1>
          <span className="mypage-top-space" />
        </div>

        {selectedChildId == null ? (
          <div className="pre-capture-empty">
            <span>☺</span>
            <h2>촬영할 자녀를 먼저 선택해 주세요</h2>
            <button className="login-button" onClick={() => onNavigate('child-profile')}>자녀 선택하기</button>
          </div>
        ) : (
          <>
            <div className={`capture-schedule-hero ${summary?.scan_due ? 'due' : 'waiting'}`}>
              <span className="capture-schedule-icon">◷</span>
              <small>{isLoading ? '권장 주기를 확인하는 중' : `${child?.name || '자녀'}의 권장 촬영 주기`}</small>
              <strong>{scheduleLabel}</strong>
              <p>{isLoading ? '잠시만 기다려 주세요.' : dueCopy}</p>
              {child?.birthDate ? (
                <em>만 {schedule.age}세 · {schedule.feature}</em>
              ) : (
                <em>생년월일 미등록 · 기본 매주 일요일 일정이 적용돼요.</em>
              )}
            </div>

            <section className="pre-capture-checklist">
              <div className="card-head"><h2>촬영 전 30초 체크</h2></div>
              <ol>
                <li><b>1</b><span><strong>식사·양치 직후는 피하기</strong><small>매번 비슷한 시간과 구강 상태에서 촬영해요.</small></span></li>
                <li><b>2</b><span><strong>새 위생 커버와 렌즈 확인</strong><small>커버 주름이나 물방울이 렌즈를 가리지 않게 해요.</small></span></li>
                <li><b>3</b><span><strong>같은 위치와 LED 밝기 유지</strong><small>지난 기록과 조건이 비슷할수록 비교가 정확해져요.</small></span></li>
              </ol>
            </section>

            <p className="capture-cycle-note">권장일이 아니어도 통증·출혈·부기 또는 외상이 있으면 상태를 기록할 수 있어요. 증상이 있으면 앱 결과를 기다리지 말고 치과에 방문해 주세요.</p>

            <button className="login-button" onClick={() => onNavigate('camera')}>촬영 시작하기</button>
            <button className="pre-capture-guide-button" onClick={() => onNavigate('care-guide')}>전체 촬영 주기와 위생 가이드 보기</button>
          </>
        )}
      </div>
    </section>
  );
}

export default PreCapturePage;
