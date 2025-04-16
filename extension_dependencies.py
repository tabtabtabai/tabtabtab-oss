from tabtabtab_lib.extension_directory import BaseExtensionDependencies
from enum import auto
class EXTENSION_DEPENDENCIES(BaseExtensionDependencies):
    """
    Enum containing all possible extension dependencies.
    """

    google_calendar_api_key = auto()
    notion_mcp_url = auto()
    calendar_mcp_url = auto() 
    anthropic_api_key = auto()
    my_location = auto()