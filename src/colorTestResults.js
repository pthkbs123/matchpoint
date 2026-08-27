export const COLOR_TEST_STORAGE_KEY = 'smileguard-color-test-results-v1';

export const PREPROCESS_LABELS = {
  original: '원본',
  wb_clahe: 'WB + CLAHE',
  wb_bilateral_clahe: 'WB + Bilateral + CLAHE',
};

export const REFERENCE_LABELS = {
  unknown: '기준 미확인',
  normal: '정상 기준',
  yellow: '황변 있음',
  gum: '잇몸 붉음',
  both: '황변·잇몸 붉음',
};

const numeric = (value) => (
  value == null || value === '' || !Number.isFinite(Number(value)) ? null : Number(value)
);

export function createColorTestRecord(response, metadata = {}) {
  return {
    id: metadata.id || `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    createdAt: metadata.createdAt || new Date().toISOString(),
    fileName: metadata.fileName || '사진',
    condition: metadata.condition || 'same',
    reference: metadata.reference || 'unknown',
    note: metadata.note || '',
    imageSize: response.image_size || null,
    comparisons: (response.comparisons || []).map((item) => ({
      mode: item.mode,
      cavityCount: numeric(item.cavity_count),
      normalCount: numeric(item.normal_count),
      yellowingIndex: numeric(item.yellowing_index),
      gumInflammationIndex: numeric(item.gum_inflammation_index),
      meanLabB: numeric(item.raw?.yellowing?.mean_lab_b),
      yellowingPixels: numeric(item.raw?.yellowing?.valid_pixels),
      meanLabA: numeric(item.raw?.gum_inflammation?.mean_lab_a),
      meanHsvH: numeric(item.raw?.gum_inflammation?.mean_hsv_h),
      meanHsvS: numeric(item.raw?.gum_inflammation?.mean_hsv_s),
      meanHsvV: numeric(item.raw?.gum_inflammation?.mean_hsv_v),
      hsvHealthScore: numeric(item.raw?.gum_inflammation?.hsv_health_score),
      labHsvGap: numeric(item.raw?.gum_inflammation?.lab_hsv_gap),
      labHsvAgreement: item.raw?.gum_inflammation?.lab_hsv_agreement || null,
      gumPixels: numeric(item.raw?.gum_inflammation?.valid_pixels),
    })),
  };
}

function stats(values) {
  const valid = values.filter((value) => value != null && Number.isFinite(value));
  if (!valid.length) return { count: 0, mean: null, min: null, max: null, range: null };
  const min = Math.min(...valid);
  const max = Math.max(...valid);
  return {
    count: valid.length,
    mean: valid.reduce((sum, value) => sum + value, 0) / valid.length,
    min,
    max,
    range: max - min,
  };
}

export function summarizeColorTests(records) {
  return Object.keys(PREPROCESS_LABELS).map((mode) => {
    const samples = records.flatMap((record) => record.comparisons || []).filter((item) => item.mode === mode);
    return {
      mode,
      sampleCount: samples.length,
      yellowing: stats(samples.map((item) => item.yellowingIndex)),
      gum: stats(samples.map((item) => item.gumInflammationIndex)),
      labB: stats(samples.map((item) => item.meanLabB)),
      labA: stats(samples.map((item) => item.meanLabA)),
      hsvS: stats(samples.map((item) => item.meanHsvS)),
      hsvHealth: stats(samples.map((item) => item.hsvHealthScore)),
    };
  });
}

function median(values) {
  const sorted = values.filter((item) => item != null && Number.isFinite(item)).sort((a, b) => a - b);
  if (!sorted.length) return null;
  const middle = Math.floor(sorted.length / 2);
  return sorted.length % 2 ? sorted[middle] : (sorted[middle - 1] + sorted[middle]) / 2;
}

export function recommendColorCalibration(records) {
  const samples = records.map((record) => ({
    reference: record.reference,
    metrics: (record.comparisons || []).find((item) => item.mode === 'wb_clahe'),
  })).filter((item) => item.metrics);
  const normal = samples.filter((item) => item.reference === 'normal');
  const yellow = samples.filter((item) => ['yellow', 'both'].includes(item.reference));
  const gum = samples.filter((item) => ['gum', 'both'].includes(item.reference));

  const candidate = (normalValues, affectedValues) => {
    const good = median(normalValues);
    const high = median(affectedValues);
    const enough = normalValues.length >= 3 && affectedValues.length >= 3;
    return {
      normalCount: normalValues.length,
      affectedCount: affectedValues.length,
      ready: enough && good != null && high != null && high > good,
      good: good == null ? null : Number(good.toFixed(1)),
      high: high == null ? null : Number(high.toFixed(1)),
    };
  };

  return {
    yellowLabB: candidate(
      normal.map((item) => item.metrics.meanLabB).filter((value) => value != null),
      yellow.map((item) => item.metrics.meanLabB).filter((value) => value != null),
    ),
    gumLabA: candidate(
      normal.map((item) => item.metrics.meanLabA).filter((value) => value != null),
      gum.map((item) => item.metrics.meanLabA).filter((value) => value != null),
    ),
    gumHsvS: candidate(
      normal.map((item) => item.metrics.meanHsvS).filter((value) => value != null),
      gum.map((item) => item.metrics.meanHsvS).filter((value) => value != null),
    ),
  };
}

export function loadColorTestRecords(storage = localStorage) {
  try {
    const value = JSON.parse(storage.getItem(COLOR_TEST_STORAGE_KEY) || '[]');
    return Array.isArray(value) ? value : [];
  } catch {
    return [];
  }
}

export function saveColorTestRecords(records, storage = localStorage) {
  storage.setItem(COLOR_TEST_STORAGE_KEY, JSON.stringify(records));
}

export function colorTestsToCsv(records) {
  const header = [
    '측정시각', '파일', '촬영조건', '참고상태', '메모', '전처리', '충치수', '정상수',
    '황변건강점수', '잇몸LAB건강점수', '잇몸HSV보조점수', 'LAB_HSV차이', 'LAB_HSV일치도',
    'LAB_b', 'LAB_a', 'HSV_H', 'HSV_S', 'HSV_V',
    '황변유효픽셀', '잇몸유효픽셀',
  ];
  const escape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
  const rows = records.flatMap((record) => (record.comparisons || []).map((item) => [
    record.createdAt,
    record.fileName,
    record.condition,
    REFERENCE_LABELS[record.reference] || record.reference,
    record.note,
    PREPROCESS_LABELS[item.mode] || item.mode,
    item.cavityCount,
    item.normalCount,
    item.yellowingIndex,
    item.gumInflammationIndex,
    item.hsvHealthScore,
    item.labHsvGap,
    item.labHsvAgreement,
    item.meanLabB,
    item.meanLabA,
    item.meanHsvH,
    item.meanHsvS,
    item.meanHsvV,
    item.yellowingPixels,
    item.gumPixels,
  ].map(escape).join(',')));
  return [header.map(escape).join(','), ...rows].join('\r\n');
}

