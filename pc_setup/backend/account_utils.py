import re


def normalize_phone(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def is_valid_mobile_phone(value: str | None) -> bool:
    return re.fullmatch(r"010\d{8}", normalize_phone(value)) is not None
