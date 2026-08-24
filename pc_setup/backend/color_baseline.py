"""자녀별 색상 Baseline 누적 평균 계산."""

REQUIRED_SAMPLES = 3


def advance_running_baseline(
    current_average: float | None,
    current_count: int,
    sample: float | None,
    required_samples: int = REQUIRED_SAMPLES,
) -> tuple[float | None, int]:
    """유효 샘플을 required_samples개까지만 누적하고 이후 평균은 고정한다."""
    count = int(current_count or 0)
    if sample is None or count >= required_samples:
        return current_average, count
    next_count = count + 1
    next_average = ((float(current_average or 0.0) * count) + sample) / next_count
    return round(next_average, 3), next_count
