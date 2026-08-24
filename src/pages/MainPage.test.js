import { render, screen, waitFor } from '@testing-library/react';
import { apiFetch } from '../api';
import MainPage from './MainPage';

jest.mock('../api', () => ({ apiFetch: jest.fn() }));
jest.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="main-trend-chart" />,
}));

const summary = {
  current_score: 95,
  total_scans: 4,
  scan_due: false,
  notification_schedule_label: '매주 일요일',
  weekly_trend: { labels: [], scores: [], scan_counts: [] },
  notifications: [{
    id: 'monthly-report:child-7:2026-07',
    type: 'monthly_report',
    title: '7월 구강 관리 리포트',
  }],
};

beforeEach(() => {
  localStorage.clear();
  apiFetch.mockImplementation((path) => {
    if (path === '/api/children') {
      return Promise.resolve({ children: [{ id: 7, name: '지우' }] });
    }
    return Promise.resolve(summary);
  });
});

test('새 월간 리포트가 있으면 메인 종 아이콘에 미확인 표시를 한다', async () => {
  render(
    <MainPage
      onNavigate={jest.fn()}
      user={{ id: 3, name: '보호자' }}
      token="test-token"
      selectedChildId={7}
      onSelectChild={jest.fn()}
    />
  );

  await waitFor(() => {
    expect(screen.getByRole('button', { name: '새 알림이 있습니다. 알림 내역으로 이동' })).toBeInTheDocument();
  });
});

test('월간 리포트 설정을 끄면 해당 알림을 미확인으로 표시하지 않는다', async () => {
  localStorage.setItem('notif_monthly_report', 'false');
  render(
    <MainPage
      onNavigate={jest.fn()}
      user={{ id: 3, name: '보호자' }}
      token="test-token"
      selectedChildId={7}
      onSelectChild={jest.fn()}
    />
  );

  await waitFor(() => {
    expect(screen.getByRole('button', { name: '알림 내역으로 이동' })).toBeInTheDocument();
  });
});
