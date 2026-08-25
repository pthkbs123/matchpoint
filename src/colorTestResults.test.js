import {
  colorTestsToCsv,
  createColorTestRecord,
  recommendColorCalibration,
  summarizeColorTests,
} from './colorTestResults';

const response = {
  image_size: { width: 640, height: 480 },
  comparisons: [
    {
      mode: 'original', cavity_count: 1, normal_count: 2,
      yellowing_index: 81, gum_inflammation_index: 72,
      raw: {
        yellowing: { mean_lab_b: 139, valid_pixels: 500 },
        gum_inflammation: {
          mean_lab_a: 148, mean_hsv_h: 2, mean_hsv_s: 120, mean_hsv_v: 180,
          hsv_health_score: 65, lab_hsv_gap: 7, lab_hsv_agreement: 'high', valid_pixels: 300,
        },
      },
    },
  ],
};

test('API 비교 결과를 저장 가능한 측정 레코드로 변환한다', () => {
  const record = createColorTestRecord(response, {
    id: 'run-1', createdAt: '2026-08-25T10:00:00Z', fileName: 'tooth.jpg', condition: 'same',
  });
  expect(record.comparisons[0]).toMatchObject({
    mode: 'original', yellowingIndex: 81, meanLabA: 148, meanHsvS: 120,
    hsvHealthScore: 65, labHsvAgreement: 'high',
  });
});

test('누적 측정에서 전처리별 점수 변동 폭을 계산한다', () => {
  const first = createColorTestRecord(response, { id: '1' });
  const second = createColorTestRecord({
    ...response,
    comparisons: [{ ...response.comparisons[0], yellowing_index: 76, gum_inflammation_index: 70 }],
  }, { id: '2' });
  const original = summarizeColorTests([first, second]).find((item) => item.mode === 'original');
  expect(original.yellowing).toMatchObject({ count: 2, mean: 78.5, range: 5 });
  expect(original.gum.range).toBe(2);
});

test('측정 결과를 LAB와 HSV 값이 포함된 CSV로 변환한다', () => {
  const csv = colorTestsToCsv([createColorTestRecord(response, { fileName: 'tooth.jpg' })]);
  expect(csv).toContain('"LAB_a"');
  expect(csv).toContain('"HSV_S"');
  expect(csv).toContain('"LAB_HSV일치도"');
  expect(csv).toContain('"tooth.jpg"');
});

test('정상과 변화 사진이 각각 3장 이상이면 실제 데이터 보정 후보를 계산한다', () => {
  const makeRecord = (id, reference, labB, labA, hsvS) => createColorTestRecord({
    image_size: response.image_size,
    comparisons: [{
      ...response.comparisons[0],
      mode: 'wb_clahe',
      raw: {
        yellowing: { mean_lab_b: labB, valid_pixels: 500 },
        gum_inflammation: { mean_lab_a: labA, mean_hsv_s: hsvS, valid_pixels: 300 },
      },
    }],
  }, { id, reference });
  const records = [
    makeRecord('n1', 'normal', 130, 138, 65),
    makeRecord('n2', 'normal', 132, 140, 70),
    makeRecord('n3', 'normal', 134, 142, 75),
    makeRecord('a1', 'both', 160, 165, 140),
    makeRecord('a2', 'both', 162, 167, 145),
    makeRecord('a3', 'both', 164, 169, 150),
  ];
  const calibration = recommendColorCalibration(records);
  expect(calibration.yellowLabB).toMatchObject({ ready: true, good: 132, high: 162 });
  expect(calibration.gumLabA).toMatchObject({ ready: true, good: 140, high: 167 });
  expect(calibration.gumHsvS).toMatchObject({ ready: true, good: 70, high: 145 });
});

