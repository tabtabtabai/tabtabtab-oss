import logging
from typing import Any, Dict, Optional, List
import asyncio
import aiohttp
import json
import base64

# Update imports to use tabtabtab_lib
from tabtabtab_lib.extension_interface import (
    ExtensionInterface,
    CopyResponse,
    PasteResponse,
    OnContextResponse,
    Notification,
    NotificationStatus,
    ImmediatePaste,
)
import anthropic

# Set up basic logging for the sample extension
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


class AddressExtension(
    ExtensionInterface
):
    """
    A sample extension demonstrating the implementation of ExtensionInterface.
    This version uses an LLM to find the address of a given copy event.
    The procress runs in the background and sends a notification response back
    via an injected SSE sender.
    """

    async def on_context_request(
        self, source_extension_id: str, context_query: Dict[str, Any]
    ) -> OnContextResponse:
        """
        Asynchronously handles context requests by logging the request
        and returning some sample data.
        """
        return None

    async def on_copy(self, context: Dict[str, Any]) -> CopyResponse:
        """
        Handles copy events. If a browser URL is detected in window_info,
        it triggers a background task to fetch content, summarize it,
        and send results via SSE. Also logs if screenshot data is present.
        """
        log.info(
            f"[{self.extension_id}] on_copy called with context keys: {list(context.keys())}"
        )
        dependencies = context.get("dependencies", {})
        anthropic_api_key = dependencies.get(
            "anthropic_api_key", ""
        )
        screenshot_data = context.get("screenshot_data", None)
        
        if anthropic_api_key:
            try:
                client = anthropic.Anthropic(api_key=anthropic_api_key)
                
                # Debug logging
                log.info(f"Screenshot data type: {type(screenshot_data)}")
                
                # Prepare the message content
                message_content = []
                
                # Add screenshot if available
                if screenshot_data:
                    if isinstance(screenshot_data, (bytes, bytearray)):
                        # Convert raw bytes to base64
                        image_data = base64.b64encode(screenshot_data).decode()
                        message_content.append({
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        })
                    elif isinstance(screenshot_data, dict):
                        # Already in the correct format
                        message_content.append({
                            "type": "image",
                            "source": screenshot_data["source"],
                        })
                    
                    log.info(f"Image data prepared successfully")
                
                # Add text prompt
                message_content.append({
                    "type": "text",
                    "text": "Please analyze this screenshot and extract any address information you can find."
                })
                
                # Create background task for API call and notification
                asyncio.create_task(self._process_image_async(
                    client=client,
                    message_content=message_content,
                    device_id=context.get("device_id"),
                    request_id=context.get("request_id")
                ))

                return CopyResponse(
                    notification=Notification(
                        request_id=context.get("request_id"),
                        title="Address Extraction",
                        detail="Processing image...",
                        content="Analyzing image for address information",
                        status=NotificationStatus.PENDING,
                    )
                )

            except Exception as e:
                log.error(f"Failed to query Anthropic API: {e}", exc_info=True)
        else:
            log.error("Anthropic API key not found.")

        return CopyResponse(
            notification=Notification(
                request_id=context.get("request_id"),
                title="Address Extraction",
                detail="Failed to process",
                content="No image data or API key available",
                status=NotificationStatus.ERROR,
            )
        )

    async def _process_image_async(
        self,
        client: anthropic.Anthropic,
        message_content: List[Dict],
        device_id: str,
        request_id: str
    ) -> None:
        """Process image with Anthropic API and send notification with results."""
        try:
            response = client.messages.create(
                model="claude-3-7-sonnet-20250219",
                max_tokens=2048,
                temperature=0.7,
                system="You are an assistant specialized in extracting address information from images and text.",
                messages=[{
                    "role": "user",
                    "content": message_content
                }],
            )
            
            await self.send_push_notification(
                device_id=device_id,
                notification=Notification(
                    request_id=request_id,
                    title="Address Extraction",
                    detail="Address analysis complete",
                    content=response.content,
                    status=NotificationStatus.READY,
                )
            )
        except Exception as e:
            log.error(f"Failed to process image with Anthropic API: {e}", exc_info=True)
            await self.send_push_notification(
                device_id=device_id,
                notification=Notification(
                    request_id=request_id,
                    title="Address Extraction",
                    detail="Failed to analyze image",
                    content=f"Error: {str(e)}",
                    status=NotificationStatus.ERROR,
                )
            )

    async def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        """
        Handles paste events by logging context and returning a response object.
        """
        return None

