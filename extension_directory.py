from tabtabtab_lib.extension_directory import (
    ExtensionDescriptor,
    BaseExtensionID,
)
from extensions.sample_extension.sample_extension import SampleExtension
from extensions.notion_mcp_extension.notion_mcp_extension import NotionMCPExtension
from extensions.calendar_mcp_extension.calendar_mcp_extension import CalendarMCPExtension
from enum import auto
from extension_dependencies import EXTENSION_DEPENDENCIES


class EXTENSION_ID(BaseExtensionID):
    """
    Enum containing all possible extension IDs.
    """

    sample_extension = auto()
    notion_mcp_extension = auto()
    calendar_mcp_extension = auto()


EXTENSION_DIRECTORY = [
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.sample_extension,
        description="Sample extension to show how to use the extension interface. It takes a copy of a web browser page (public only) and summarizes it.",
        dependencies=[],
        extension_class=SampleExtension,
    ),
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.notion_mcp_extension,
        description="Notion extension, takes a copy of any text and adds it to a Notion page.",
        dependencies=[EXTENSION_DEPENDENCIES.notion_mcp_url, EXTENSION_DEPENDENCIES.anthropic_api_key],
        extension_class=NotionMCPExtension,
    ),
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.calendar_mcp_extension,
        description="Calendar extension, copy a text and add it to your calender, paste a text and get calendar aware responses.",
        dependencies=[EXTENSION_DEPENDENCIES.calendar_mcp_url, EXTENSION_DEPENDENCIES.anthropic_api_key, EXTENSION_DEPENDENCIES.my_location],
        extension_class=CalendarMCPExtension,
    )
]
