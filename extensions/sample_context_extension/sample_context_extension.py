from typing import Dict, Any
from tabtabtab_lib.extension_interface import (
    ExtensionInterface,
    CopyResponse,
    PasteResponse,
    OnContextResponse,
    Notification,
    NotificationStatus,
)
import logging

logger = logging.getLogger(__name__)


class SampleContextExtension(ExtensionInterface):
    """A dummy extension for testing and development purposes."""

    async def on_context_request(
        self, source_extension_id: str, context_query: Dict[str, Any]
    ) -> OnContextResponse:
        logger.info(
            f"Dummy extension received context request from {source_extension_id} with context: {context_query['dependencies']}"
        )
        """Return dummy context for testing."""
        dummy_context = OnContextResponse.ExtensionContext(
            description="Here is my favorite color",
            context="My favorite color is blue",
        )
        return OnContextResponse(contexts=[dummy_context])

    async def on_copy(self, context: Dict[str, Any]) -> CopyResponse:
        """Handle copy event with dummy response."""
        logger.info(f"Dummy extension received copy event")
        return None

    async def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        """Handle paste event with dummy content."""
        logger.info(f"Dummy extension received paste event")
        return None
