"""앱 내 월간 리포트 알림 생성."""
from datetime import date, timedelta


def _month_start(day: date) -> date:
    return day.replace(day=1)


def _previous_month_range(day: date) -> tuple[date, date]:
    end = _month_start(day) - timedelta(days=1)
    return _month_start(end), end


def build_monthly_report_notification(
    measurements: list[dict],
    today: date,
    scope_key: str,
) -> dict | None:
    """지난달 기록이 있을 때만 한 달에 하나의 안정적인 알림을 만든다."""
    report_start, report_end = _previous_month_range(today)
    comparison_end = report_start - timedelta(days=1)
    comparison_start = _month_start(comparison_end)

    report_scores = [
        float(item["score"])
        for item in measurements
        if report_start <= item["date"] <= report_end
    ]
    if not report_scores:
        return None

    comparison_scores = [
        float(item["score"])
        for item in measurements
        if comparison_start <= item["date"] <= comparison_end
    ]
    average_score = round(sum(report_scores) / len(report_scores))
    comparison_average = (
        round(sum(comparison_scores) / len(comparison_scores))
        if comparison_scores
        else None
    )
    score_change = (
        average_score - comparison_average
        if comparison_average is not None
        else None
    )

    if score_change is None:
        change_message = "첫 월간 리포트가 완성됐어요."
    elif score_change > 0:
        change_message = f"그 전 달보다 평균이 {score_change}점 올랐어요."
    elif score_change < 0:
        change_message = f"그 전 달보다 평균이 {abs(score_change)}점 낮아졌어요."
    else:
        change_message = "그 전 달과 같은 평균을 유지했어요."

    month_key = report_start.strftime("%Y-%m")
    return {
        "id": f"monthly-report:{scope_key}:{month_key}",
        "date": today.isoformat(),
        "date_label": f"{report_start.month}월 리포트",
        "title": f"{report_start.month}월 구강 관리 리포트",
        "message": f"{len(report_scores)}회 촬영 · 평균 {average_score}점. {change_message}",
        "type": "monthly_report",
        "report_month": month_key,
        "scan_count": len(report_scores),
        "score": average_score,
        "score_change": score_change,
        "action": "report",
    }
