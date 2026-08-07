from enum import StrEnum


class CrowdLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


CROWD_THRESHOLDS = {
    CrowdLevel.LOW: 250,
    CrowdLevel.MEDIUM: 700,
}


def classify_crowd_count(pedestrian_count: int) -> CrowdLevel:
    if pedestrian_count <= CROWD_THRESHOLDS[CrowdLevel.LOW]:
        return CrowdLevel.LOW
    if pedestrian_count <= CROWD_THRESHOLDS[CrowdLevel.MEDIUM]:
        return CrowdLevel.MEDIUM
    return CrowdLevel.HIGH
