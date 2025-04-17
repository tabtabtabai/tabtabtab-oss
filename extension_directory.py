from tabtabtab_lib.extension_directory import (
    ExtensionDescriptor,
)
from extensions.sample_extension.sample_extension import SampleExtension
from extensions.sample_context_extension.sample_context_extension import (
    SampleContextExtension,
)
from extensions.notion_mcp_extension.notion_mcp_extension import NotionMCPExtension
from extensions.calendar_mcp_extension.calendar_mcp_extension import (
    CalendarMCPExtension,
)
from extensions.address_extension.address_extension import AddressExtension
from extensions.fashion_ideas.fashion_ideas import FashionIdeasExtension
from extension_constants import EXTENSION_DEPENDENCIES, EXTENSION_ID
from extensions.translation_extension.translation_extension import TranslationExtension


EXTENSION_DIRECTORY = [
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.sample_extension,
        description="Sample extension to show how to use the extension interface. It takes a copy of a web browser page (public only) and summarizes it.",
        dependencies=[],
        extension_class=SampleExtension,
    ),
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.sample_context_extension,
        description="Sample context extension to show how to use the extension as context provider.",
        dependencies=[],
        extension_class=SampleContextExtension,
    ),
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.notion_mcp_extension,
        description="Notion extension, pushes any text that is copied to the right place in Notion",
        dependencies=[
            EXTENSION_DEPENDENCIES.notion_mcp_url,
            EXTENSION_DEPENDENCIES.anthropic_api_key,
        ],
        extension_class=NotionMCPExtension,
    ),
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.calendar_mcp_extension,
        description="Calendar extension, copy a text and add it to your calender, paste a text and get calendar aware responses.",
        dependencies=[
            EXTENSION_DEPENDENCIES.calendar_mcp_url,
            EXTENSION_DEPENDENCIES.anthropic_api_key,
            EXTENSION_DEPENDENCIES.my_location,
        ],
        extension_class=CalendarMCPExtension,
    ),
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.fashion_ideas,
        description="Fashion ideas extension, copy a text and get fashion ideas.",
        dependencies=[],
        extension_class=FashionIdeasExtension,
    ),
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.address_extension,
        description="Address extension, extract address from an image",
        dependencies=[
            EXTENSION_DEPENDENCIES.anthropic_api_key,
        ],
        extension_class=AddressExtension,
    ),
    ExtensionDescriptor(
        extension_id=EXTENSION_ID.translation_extension,
        description="Translation extension, translate text to any language.",
        dependencies=[
            EXTENSION_DEPENDENCIES.anthropic_api_key,
        ],
        extension_class=TranslationExtension,
    ),
]
