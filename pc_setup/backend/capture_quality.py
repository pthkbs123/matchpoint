MIN_NORMAL_TOOTH_DETECTIONS = 1


def assess_capture_quality(detections: list[dict]) -> dict:
    """충치 후보만 나온 사진을 구강 사진으로 확정하지 않도록 한다.

    현재 모델의 normal 클래스는 일반 치아 영역이므로, 이 영역이 하나도
    없다면 치아가 아닌 물체를 cavity로 오탐했을 가능성을 우선한다.
    """
    normal_count = sum(1 for detection in detections if detection.get("class") == "normal")
    if normal_count < MIN_NORMAL_TOOTH_DETECTIONS:
        return {
            "valid": False,
            "code": "insufficient_tooth_regions",
            "message": "치아 영역이 충분히 확인되지 않았습니다.",
        }

    return {
        "valid": True,
        "code": "accepted",
        "message": "치아 영역이 확인되었습니다.",
    }
