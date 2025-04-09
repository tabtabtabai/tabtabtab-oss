from dataclasses import dataclass
from typing import List, Type
from enum import Enum, auto

from open_sourced.extension_interface import ExtensionInterface
from open_sourced.extensions.sample_extension.sample_extension import SampleExtension


class EXTENSION_ID(Enum):
    """
    Enum containing all possible extension IDs.
    """
    SAMPLE_EXTENSION = auto()


class EXTENSION_DEPENDENCIES(Enum):
    """
    Enum containing all possible extension dependencies.
    """
    GOOGLE_CALENDAR_API_KEY = auto()


@dataclass
class ExtensionDescriptor:
    extension_id: EXTENSION_ID
    description: str
    dependencies: List[EXTENSION_DEPENDENCIES]
    extension_class: Type[ExtensionInterface]


EXTENSION_DIRECTORY = [
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.SAMPLE_EXTENSION,
        description="Sample extension",
        dependencies=[EXTENSION_DEPENDENCIES.GOOGLE_CALENDAR_API_KEY],
        extension_class=SampleExtension,
    )
]