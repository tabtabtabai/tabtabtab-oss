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
# Update LLM imports
from tabtabtab_lib.llm import LLMModel
from tabtabtab_lib.llm_interface import LLMProcessorInterface, LLMContext
from tabtabtab_lib.sse_interface import SSESenderInterface

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
        log.info(
            f"[{self.extension_id}] Received async context request from "
            f"'{source_extension_id}'"
        )

        response = OnContextResponse(
            contexts=[
                OnContextResponse.ExtensionContext(
                    description="some_context_key", context="some_context_value_async"
                ),
                OnContextResponse.ExtensionContext(
                    description="some_other_context_key",
                    context=json.dumps({"some_nested_key": "some_nested_value_async"}),
                ),
            ]
        )
        return response

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
                
                response = client.messages.create(
                    model="claude-3-7-sonnet-20250219",  # Updated to correct model name
                    max_tokens=2048,
                    temperature=0.7,
                    system="You are an assistant specialized in extracting address information from images and text.",
                    messages=[{
                        "role": "user",
                        "content": message_content
                    }],
                )
                log.info(f"Anthropic API response: {response}")
            except Exception as e:
                log.error(f"Failed to query Anthropic API: {e}", exc_info=True)
        else:
            log.error("Anthropic API key not found.")

        return CopyResponse(
            notification=Notification(
                request_id=context.get("request_id"),
                title="Address Extraction",
                detail="Address analysis complete",
                content=response.content if 'response' in locals() else "Failed to analyze image",
                status=NotificationStatus.ERROR if 'response' not in locals() else NotificationStatus.READY,
            )
        )

    async def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        """
        Handles paste events by logging context and returning a response object.
        """
        log.info(f"[{self.extension_id}] on_paste triggered.")

        device_id = context.get("device_id")
        request_id = context.get("request_id")

        # example of doing a long running task
        try:
            asyncio.create_task(self._sample_long_running_task(device_id, request_id))
            log.info(
                f"[{self.extension_id}][Req:{request_id}] Background task created successfully."
            )

        except Exception as e:
            log.error(
                f"[{self.extension_id}][Req:{request_id}] Failed to create background task: {e}",
                exc_info=True,
            )
            return PasteResponse(
                paste=Notification(
                    request_id=request_id,
                    title="Sample",
                    detail=f"Internal error",
                    content=f"Failed to create background task: {e}",
                    status=NotificationStatus.ERROR,
                )
            )

        return PasteResponse(
            paste=Notification(
                request_id=request_id,
                title="Sample",
                detail="Request received",
                content="Starting background paste task. Extension Context: "
                + str(context.get("extensions_context")),
                status=NotificationStatus.PENDING,
            )
        )

    async def _summarize_url_content_async(
        self, browser_url: str, device_id: str, request_id: str
    ) -> None:
        """
        Asynchronous helper to fetch URL content, summarize it using LLM,
        and send results/status via SSE. Runs in the background.
        """
        log_prefix = (
            f"[{self.extension_id}][Req:{request_id}]"  # Add request ID to logs
        )

        if not browser_url or not isinstance(browser_url, str):
            log.warning(f"{log_prefix} No valid browser URL provided for processing.")
            return

        log.info(f"{log_prefix} Starting background processing for URL: {browser_url}")

        # --- Fetch URL Content ---
        text_content: Optional[str] = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(browser_url, timeout=30.0) as response:
                    if response.status == 200:
                        try:
                            text_content = await response.text(
                                encoding=response.charset or "utf-8", errors="ignore"
                            )
                        except Exception as decode_err:
                            log.error(
                                f"{log_prefix} Error decoding content from URL {browser_url}: {decode_err}"
                            )
                            return

                        log.info(
                            f"{log_prefix} Successfully fetched URL content (length: {len(text_content)})"
                        )
                    else:
                        log.error(
                            f"{log_prefix} Failed to fetch URL: {response.status}"
                        )
                        await self.send_push_notification(
                            device_id=device_id,
                            notification=Notification(
                                request_id=request_id,
                                title="Sample",
                                detail=f"Failed to fetch URL: {response.status}",
                                content="",
                                status=NotificationStatus.ERROR,
                            ),
                        )
                        return
        except ImportError:
            log.error(
                f"{log_prefix} aiohttp library not found. Cannot fetch URL content."
            )
            return
        except Exception as e:
            log.error(f"{log_prefix} Error fetching URL content: {e}", exc_info=True)
            return
        # --- End Fetch URL Content ---

        # --- LLM Integration ---
        if not text_content:
            log.warning(f"{log_prefix} No text content fetched from URL to process.")
            return

        content_summarization_prompt = """
        You are an AI assistant tasked with finding the address of a given copy event.
        Analyze the provided text context and generate a concise address.
        Respond ONLY with the address text. Do not include introductory phrases like "Here is the address:".
        """
        llm_context = LLMContext(text=text_content)
        summary_result: Optional[str] = None  # Store result here

        if not self.llm_processor:
            log.error(f"{log_prefix} LLM Processor not configured/injected.")
            return

        try:
            log.info(f"{log_prefix} Calling LLM to find address...")
            llm_response = await self.llm_processor.process(
                system_prompt=content_summarization_prompt,
                message="Find the address in the following content:",
                contexts=[llm_context],
                model=LLMModel.GEMINI_FLASH,  # Or your preferred model
                stream=False,
            )

            if not isinstance(llm_response, str) or not llm_response.strip():
                log.error(f"{log_prefix} LLM response was not a non-empty string.")
                return  # Stop if LLM response is invalid

            summary_result = llm_response.strip()
            log.info(
                f"{log_prefix} LLM summary received: {summary_result[:150]}..."
            )  # Log truncated summary

            # --- Send Final Result via SSE ---
            log.info(f"{log_prefix} Successfully generated address.")
            await self.send_push_notification(
                device_id=device_id,
                notification=Notification(
                    request_id=request_id,
                    title="Address",
                    detail="Address found",
                    content=summary_result,
                    status=NotificationStatus.READY,
                ),
            )

        except Exception as e:
            log.exception(f"{log_prefix} Error during LLM processing: {e}")

    async def _sample_long_running_task(self, device_id: str, request_id: str) -> None:
        log.info(f"[{self.extension_id}][Req:{request_id}] Starting long running task.")
        await asyncio.sleep(10)
        log.info(
            f"[{self.extension_id}][Req:{request_id}] Long running task completed."
        )

        await self.send_push_notification(
            device_id=device_id,
            notification=Notification(
                request_id=request_id,
                title="Address",
                detail="Long running task",
                content="Task completed after 10 seconds",
                status=NotificationStatus.READY,
            ),
        )
