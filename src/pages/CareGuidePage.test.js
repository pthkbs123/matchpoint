import { fireEvent, render, screen } from '@testing-library/react';
import CareGuidePage from './CareGuidePage';

test('촬영 가이드 내용을 탭별로 나누어 표시한다', () => {
  render(<CareGuidePage onNavigate={jest.fn()} />);

  expect(screen.getByText('안전하고 선명하게 촬영해요')).toBeInTheDocument();
  expect(screen.queryByText('연령별 권장 촬영 주기')).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('tab', { name: '권장 주기' }));
  expect(screen.getByText('연령별 권장 촬영 주기')).toBeInTheDocument();
  expect(screen.queryByText('안전하고 선명하게 촬영해요')).not.toBeInTheDocument();

  fireEvent.click(screen.getByRole('tab', { name: '재촬영 기준' }));
  expect(screen.getByText('이럴 때는 다시 촬영해 주세요')).toBeInTheDocument();
  expect(screen.queryByText('연령별 권장 촬영 주기')).not.toBeInTheDocument();
});
