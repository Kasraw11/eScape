from app.core.crowd import CrowdLevel, classify_crowd_count


def test_classify_crowd_count_uses_central_thresholds() -> None:
    assert classify_crowd_count(100) == CrowdLevel.LOW
    assert classify_crowd_count(500) == CrowdLevel.MEDIUM
    assert classify_crowd_count(1000) == CrowdLevel.HIGH
