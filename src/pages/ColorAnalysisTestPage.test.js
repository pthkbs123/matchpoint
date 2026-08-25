import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { apiFetch } from '../api';
import ColorAnalysisTestPage from './ColorAnalysisTestPage';

jest.mock('../api', () => ({ apiFetch: jest.fn() }));

beforeEach(() => {
  localStorage.clear();
  jest.restoreAllMocks();
  apiFetch.mockReset();
});

test('현재 개인 기준 상태를 표시하고 기존 기록 삭제 없이 재설정을 요청한다', async () => {
  apiFetch.mockImplementation((path) => {
    if (path.startsWith('/api/color-baseline/status')) {
      return Promise.resolve({
        baseline: {
          ready: true,
          generation: 1,
          yellowing: { sample_count: 3 },
          gum_inflammation: { sample_count: 3 },
        },
      });
    }
    if (path === '/api/color-baseline/reset') {
      return Promise.resolve({
        message: '기존 촬영 기록은 유지하고 개인 기준 수집을 새로 시작합니다.',
        baseline: {
          ready: false,
          generation: 2,
          yellowing: { sample_count: 0 },
          gum_inflammation: { sample_count: 0 },
        },
      });
    }
    return Promise.reject(new Error('예상하지 못한 요청'));
  });
  jest.spyOn(window, 'confirm').mockReturnValue(true);

  render(
    <ColorAnalysisTestPage
      onNavigate={jest.fn()}
      token="test-token"
      selectedChildId={7}
    />
  );

  expect(await screen.findByText('개인 3회 기준 사용 중')).toBeInTheDocument();
  fireEvent.click(screen.getByRole('button', { name: '기준 다시 만들기' }));

  await waitFor(() => {
    expect(apiFetch).toHaveBeenCalledWith('/api/color-baseline/reset', expect.objectContaining({
      token: 'test-token',
      method: 'POST',
      body: JSON.stringify({ child_id: 7 }),
    }));
  });
  expect(await screen.findByText('개인 기준 수집 중')).toBeInTheDocument();
  expect(screen.getByText(/기존 촬영 기록은 유지/)).toBeInTheDocument();
});

