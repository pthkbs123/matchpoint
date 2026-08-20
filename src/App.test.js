import { act, fireEvent, render, screen } from '@testing-library/react';
import App from './App';

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  window.history.replaceState(null, document.title, '/');
});

test('로그인 화면을 표시한다', () => {
  render(<App />);
  expect(screen.getByRole('heading', { name: /건강한 미소를/ })).toBeInTheDocument();
  expect(screen.getByRole('button', { name: '로그인' })).toBeInTheDocument();
});

test('브라우저 뒤로가기로 이전 앱 화면을 복원한다', () => {
  render(<App />);
  const loginHistoryState = window.history.state;

  fireEvent.click(screen.getByRole('button', { name: '회원가입' }));
  expect(screen.getByRole('heading', { name: /계정을 만들고/ })).toBeInTheDocument();
  expect(window.history.state.smileguardPage).toBe('signup');

  act(() => {
    window.history.replaceState(loginHistoryState, document.title, '/');
    window.dispatchEvent(new PopStateEvent('popstate', { state: loginHistoryState }));
  });

  expect(screen.getByRole('button', { name: '로그인' })).toBeInTheDocument();
});
