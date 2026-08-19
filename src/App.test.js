import { render, screen } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
});

test('로그인 화면을 표시한다', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: /건강한 미소를/ })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '로그인' })).toBeInTheDocument();
});
