"""Conference configuration and management."""

from typing import Dict, Any
from dataclasses import dataclass


@dataclass
class ConferenceConfig:
    """Configuration for a specific conference."""

    name: str
    area_chair_url: str
    display_name: str = None

    def __post_init__(self):
        if self.display_name is None:
            self.display_name = self.name.replace("_", " ").title()


# Conference configurations
CONFERENCE_CONFIGS: Dict[str, ConferenceConfig] = {
    "cvpr_2026": ConferenceConfig(
        name="cvpr_2026",
        area_chair_url="https://openreview.net/group?id=thecvf.com/CVPR/2026/Conference/Area_Chairs",
        display_name="CVPR 2026",
    ),
}


def get_conference_config(conference_name: str) -> ConferenceConfig:
    """Get configuration for a specific conference."""
    if conference_name not in CONFERENCE_CONFIGS:
        available = ", ".join(list(CONFERENCE_CONFIGS.keys()))
        raise ValueError(
            f"Conference '{conference_name}' not supported. Available: {available}"
        )
    return CONFERENCE_CONFIGS[conference_name]


def list_available_conferences() -> list[str]:
    """List all available conferences."""
    return list(CONFERENCE_CONFIGS.keys())


def get_default_conference() -> str:
    """Get the default conference name."""
    return "cvpr_2026"
