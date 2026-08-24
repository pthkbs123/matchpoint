import { fireEvent, render, screen } from '@testing-library/react';
import { apiFetch } from '../api';
import NotificationPage from './NotificationPage';

jest.mock('../api', () => ({ apiFetch: jest.fn() }));

const monthlyNotification = {
  id: 'monthly-report:child-7:2026-07',
  date_label: '7월 리포트',
  title: '7월 구강 관리 리포트',
  message: '4회 촬영 · 평균 95점. 그 전 달보다 평균이 3점 올랐어요.',
  type: 'monthly_report',
  report_month: '2026-07',
  score_change: 3,
};

beforeEach(() => {
  localStorage.clear();
  apiFetch.mockResolvedValue({
    notifications: [monthlyNotification],
    notification_schedule_label: '매주 일요일',
  });
});

test('월간 리포트 알림을 표시하고 리포트 화면으로 이동한다', async () => {
  const onNavigate = jest.fn();
  const onOpenMonthlyReport = jest.fn();
  render(
    <NotificationPage
      onNavigate={onNavigate}
      onOpenMonthlyReport={onOpenMonthlyReport}
      token="test-token"
      user={{ id: 3 }}
      selectedChildId={7}
    />
  );

  expect(await screen.findByText('7월 구강 관리 리포트')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '보기 ›' }));
  expect(onOpenMonthlyReport).toHaveBeenCalledWith('2026-07');
});

test('월간 리포트 알림을 별도로 끌 수 있다', async () => {
  render(
    <NotificationPage
      onNavigate={jest.fn()}
      token="test-token"
      user={{ id: 3 }}
      selectedChildId={7}
    />
  );

  const toggle = await screen.findByRole('checkbox', { name: /월간 리포트/ });
  fireEvent.click(toggle);

  expect(toggle).not.toBeChecked();
  expect(localStorage.getItem('notif_monthly_report')).toBe('false');
  expect(screen.queryByText('7월 구강 관리 리포트')).not.toBeInTheDocument();
});
