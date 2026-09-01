import { fireEvent, render, screen } from '@testing-library/react';
import CapturePreviewPage from './CapturePreviewPage';


test('분석 전 사진을 좌우로 회전할 수 있다', () => {
  const onRotate = jest.fn();
  render(
    <CapturePreviewPage
      onNavigate={jest.fn()}
      capturedUrl="blob:captured-image"
      onRotate={onRotate}
    />
  );

  fireEvent.click(screen.getByRole('button', { name: '↶ 왼쪽 회전' }));
  fireEvent.click(screen.getByRole('button', { name: '오른쪽 회전 ↷' }));

  expect(onRotate).toHaveBeenNthCalledWith(1, -90);
  expect(onRotate).toHaveBeenNthCalledWith(2, 90);
});
