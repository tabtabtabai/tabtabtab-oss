from dataclasses import dataclass
from typing import List, Type

from tabtabtab_lib.extension_interface import ExtensionInterface
from tabtabtab_lib.extension_directory import (
    ExtensionDescriptor,
    BaseExtensionID,
    BaseExtensionDependencies,
)
from extensions.sample_extension.sample_extension import SampleExtension
from enum import Enum, auto


class EXTENSION_ID(BaseExtensionID):
    """
    Enum containing all possible extension IDs.
    """

    SAMPLE_EXTENSION = auto()


class EXTENSION_DEPENDENCIES(BaseExtensionDependencies):
    """
    Enum containing all possible extension dependencies.
    """

    GOOGLE_CALENDAR_API_KEY = auto()


EXTENSION_DIRECTORY = [
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.SAMPLE_EXTENSION,
        description="Sample extension",
        dependencies=[EXTENSION_DEPENDENCIES.GOOGLE_CALENDAR_API_KEY],
        extension_class=SampleExtension,
    )
]
