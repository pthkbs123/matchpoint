import { fireEvent, render, screen } from '@testing-library/react';
import { apiFetch } from '../api';
import { isCharacterFeedbackEnabled } from '../feedbackSettings';
import ChildProfilePage from './ChildProfilePage';

jest.mock('../api', () => ({ apiFetch: jest.fn() }));

beforeEach(() => {
  localStorage.removeItem('smileguard-character-feedback-enabled');
  localStorage.removeItem('smileguard-child-feedback-settings');
  apiFetch.mockResolvedValue({
    children: [{
      id: 7,
      name: '지우',
      birthDate: '2021-05-12',
      reminderWeekday: 6,
      colorBaseline: { yellowingSampleCount: 2, gumSampleCount: 1 },
    }],
  });
});

test('모든 자녀에게 적용되는 캐릭터 피드백 토글을 한 번만 표시한다', async () => {
  render(
    <ChildProfilePage
      onNavigate={jest.fn()}
      onBack={jest.fn()}
      token="test-token"
      selectedChildId={7}
      onSelectChild={jest.fn()}
    />
  );

  const toggles = await screen.findAllByRole('checkbox', { name: /캐릭터 피드백/ });
  expect(toggles).toHaveLength(1);
  const [toggle] = toggles;
  expect(toggle).toBeChecked();

  fireEvent.click(toggle);

  expect(toggle).not.toBeChecked();
  expect(isCharacterFeedbackEnabled()).toBe(false);
  expect(screen.getByRole('status')).toHaveTextContent('모든 자녀');
  expect(screen.getByText('치아 색상 2/3 · 잇몸 색상 1/3')).toBeInTheDocument();
});
