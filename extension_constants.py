from tabtabtab_lib.extension_directory import BaseExtensionDependencies, BaseExtensionID
from enum import auto


class EXTENSION_DEPENDENCIES(BaseExtensionDependencies):
    """
    Enum containing all possible extension dependencies.
    """

    google_calendar_api_key = auto()
    notion_mcp_url = auto()
    calendar_mcp_url = auto()
    anthropic_api_key = auto()
    bitly_token = "03ac018d7c63bb34762ea043e111ed2df7eaaadd"
    my_location = auto()


class EXTENSION_ID(BaseExtensionID):
    """
    Enum containing all possible extension IDs.
    """

    sample_extension = auto()
    notion_mcp_extension = auto()
    calendar_mcp_extension = auto()
    sample_context_extension = auto()
    rudra_extension = auto()
