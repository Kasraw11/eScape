"""Manual opening-hours overrides for high-value refuge locations.

These entries are intentionally small and conservative. They let us surface
useful opening-hour information for places we trust without depending on
Google APIs or shaky scraping.
"""

from __future__ import annotations

REFUGE_HOURS_OVERRIDES = {
    "state library victoria": {
        "source": "manual override",
        "opening_hours": "Mo-Su 10:00-18:00",
        "opening_hours_pretty": "Daily 10:00-18:00",
    },
    "lincoln square": {
        "source": "manual override",
        "opening_hours": "24/7",
        "opening_hours_pretty": "Open 24 hours daily",
    },
    "university square": {
        "source": "manual override",
        "opening_hours": "24/7",
        "opening_hours_pretty": "Open 24 hours daily",
    },
    "flagstaff gardens": {
        "source": "manual override",
        "opening_hours": "24/7",
        "opening_hours_pretty": "Open 24 hours daily",
    },
}
