import logging
from typing import Any, Dict, Optional, List
import asyncio
import aiohttp
import json

# Assuming the interface and response models are importable
from open_sourced.extension_interface import (
    ExtensionInterface,
    CopyResponse,
    PasteResponse,
)
# Import LLM components from open_sourced
from open_sourced.llm import LLMModel
from open_sourced.llm_interface import LLMProcessorInterface, LLMContext
from open_sourced.sse_interface import SSESenderInterface

# Set up basic logging for the sample extension
logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

class SampleExtension(ExtensionInterface):
    """
    A sample extension demonstrating the implementation of ExtensionInterface.
    This version uses an LLM to summarize the content of a URL
    detected in on_copy, running in the background and sending the
    summary back via an injected SSE sender.
    """
    extension_id: str = "sample_extension"

    def __init__(self, sse_sender: SSESenderInterface, llm_processor: LLMProcessorInterface):
        """
        Initializes the SampleExtension.

        Args:
            sse_sender: An object conforming to the SSESenderInterface
                        for sending notifications back to the client.
            llm_processor: An object conforming to the LLMProcessorInterface
                           for interacting with language models.
        """
        self.api_key: Optional[str] = None
        self.llm_processor = llm_processor # Store the injected LLM processor
        self.sse_sender = sse_sender # Store the injected SSE sender
        log.info(f"[{self.extension_id}] Initializing...")

    def setup(self, config: Dict[str, Any]) -> None:
        """
        Stores configuration, specifically looking for an API key.
        """
        log.info(f"[{self.extension_id}] Setting up with config: {config}")
        self.api_key = config.get("api_key")
        if self.api_key:
            log.info(f"[{self.extension_id}] API key configured.")
        else:
            log.warning(f"[{self.extension_id}] API key not found in config.")

    async def _send_sse_notification(self, device_id: str, request_id: str, message: str, status: str = "info", details: Optional[Dict] = None):
        """Helper to send SSE notifications using the injected sender."""
        if not device_id or not request_id:
            log.error(f"[{self.extension_id}] Cannot send SSE notification: Missing device_id or request_id.")
            return
        if not self.sse_sender:
             log.error(f"[{self.extension_id}] Cannot send SSE notification: SSE sender not configured.")
             return

        payload = {
            "extension_id": self.extension_id,
            "request_id": request_id,
            "message": message,
            "status": status, # e.g., "info", "success", "error", "progress"
            "details": details or {} # Optional dictionary for structured data
        }
        try:
            # Use the injected sse_sender
            await self.sse_sender.send_event(
                device_id=device_id,
                event_name="extension_notification", # Standardized event name
                data=payload
            )
            log.info(f"[{self.extension_id}] SSE notification sent via interface to device {device_id} (Request ID: {request_id}): {message}")
        except Exception as e:
            log.error(f"[{self.extension_id}] Failed to send SSE notification via interface to device {device_id} (Request ID: {request_id}): {e}", exc_info=True)

    async def _summarize_url_content_async(self, browser_url: str, device_id: str, request_id: str) -> None:
        """
        Asynchronous helper to fetch URL content, summarize it using LLM,
        and send results/status via SSE. Runs in the background.
        """
        log_prefix = f"[{self.extension_id}][Req:{request_id}]" # Add request ID to logs

        if not browser_url or not isinstance(browser_url, str):
            log.warning(f"{log_prefix} No valid browser URL provided for processing.")
            await self._send_sse_notification(device_id, request_id, "No valid URL provided.", status="error")
            return

        log.info(f"{log_prefix} Starting background processing for URL: {browser_url}")

        # --- Fetch URL Content ---
        text_content: Optional[str] = None
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(browser_url, timeout=30.0) as response:
                    if response.status == 200:
                        try:
                            text_content = await response.text(encoding=response.charset or 'utf-8', errors='ignore')
                        except Exception as decode_err:
                            log.error(f"{log_prefix} Error decoding content from URL {browser_url}: {decode_err}")
                            await self._send_sse_notification(device_id, request_id, f"Error decoding content from URL.", status="error")
                            return

                        log.info(f"{log_prefix} Successfully fetched URL content (length: {len(text_content)})")
                        await self._send_sse_notification(device_id, request_id, "URL content fetched.", status="progress")
                    else:
                        log.error(f"{log_prefix} Failed to fetch URL: {response.status}")
                        await self._send_sse_notification(device_id, request_id, f"Failed to fetch URL (Status: {response.status}).", status="error")
                        return
        except ImportError:
             log.error(f"{log_prefix} aiohttp library not found. Cannot fetch URL content.")
             await self._send_sse_notification(device_id, request_id, "Internal error: Missing required library.", status="error")
             return
        except asyncio.TimeoutError:
            log.error(f"{log_prefix} Timeout fetching URL content from {browser_url}")
            await self._send_sse_notification(device_id, request_id, f"Timeout fetching URL.", status="error")
            return
        except Exception as e:
            log.error(f"{log_prefix} Error fetching URL content: {e}", exc_info=True)
            await self._send_sse_notification(device_id, request_id, f"Error fetching URL: {e}", status="error")
            return
        # --- End Fetch URL Content ---


        # --- LLM Integration ---
        if not text_content:
             log.warning(f"{log_prefix} No text content fetched from URL to process.")
             await self._send_sse_notification(device_id, request_id, "No content found at URL.", status="warning")
             return

        content_summarization_prompt = """
        You are an AI assistant tasked with summarizing web page content.
        Analyze the provided text context and generate a concise summary.
        If the content covers multiple distinct topics, structure your summary to reflect this.
        You can use bullet points or numbered lists for different topics if appropriate.
        Aim for clarity and brevity, capturing the main points of the text.
        Respond ONLY with the summary text. Do not include introductory phrases like "Here is the summary:".
        """
        llm_context = LLMContext(text=text_content)
        summary_result: Optional[str] = None # Store result here

        if not self.llm_processor:
            log.error(f"{log_prefix} LLM Processor not configured/injected.")
            await self._send_sse_notification(device_id, request_id, "Internal error: AI processor not available.", status="error")
            return

        try:
            log.info(f"{log_prefix} Calling LLM to summarize content...")
            await self._send_sse_notification(device_id, request_id, "Summarizing content...", status="progress")
            llm_response = await self.llm_processor.process(
                system_prompt=content_summarization_prompt,
                message="Summarize the following content, grouping by topic if applicable:",
                contexts=[llm_context],
                model=LLMModel.GEMINI_FLASH, # Or your preferred model
                stream=False,
            )

            if not isinstance(llm_response, str) or not llm_response.strip():
                 log.error(f"{log_prefix} LLM response was not a non-empty string.")
                 await self._send_sse_notification(device_id, request_id, "Failed to get valid summary from AI.", status="error")
                 return # Stop if LLM response is invalid

            summary_result = llm_response.strip()
            log.info(f"{log_prefix} LLM summary received: {summary_result[:150]}...") # Log truncated summary

            # --- Send Final Result via SSE ---
            log.info(f"{log_prefix} Successfully generated summary.")
            await self._send_sse_notification(
                device_id,
                request_id,
                f"Content summary generated.",
                status="success",
                details={"summary": summary_result}
            )

        except Exception as e:
            log.exception(f"{log_prefix} Error during LLM processing: {e}")
            await self._send_sse_notification(device_id, request_id, f"An error occurred during AI analysis: {e}", status="error")
        # --- End LLM Integration ---

    def on_context_request(
        self, source_extension_id: str, context_query: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handles context requests by logging the request.
        """
        log.info(
            f"[{self.extension_id}] Received context request from "
            f"'{source_extension_id}' with query: {context_query}"
        )
        return {}


    async def on_copy(self, context: Dict[str, Any]) -> CopyResponse:
        """
        Handles copy events. If a browser URL is detected in window_info,
        it triggers a background task to fetch content, summarize it,
        and send results via SSE. Also logs if screenshot data is present.
        """
        log.info(f"[{self.extension_id}] on_copy called with context keys: {list(context.keys())}")

        # Extract necessary info from context provided by extensions_manager
        device_id = context.get("device_id")
        request_id = context.get("request_id")
        window_info = context.get("window_info", {}) # Should be a dict now
        browser_url = window_info.get("accessibilityData", {}).get("browser_url") if isinstance(window_info, dict) else None
        screenshot_data: Optional[bytes] = context.get("screenshot_data") # <-- Access screenshot data

        # Log whether screenshot data was received
        if screenshot_data:
            log.info(f"[{self.extension_id}][Req:{request_id}] Received screenshot data ({len(screenshot_data)} bytes).")
            # Example: You could potentially pass screenshot_data to another function
            # if self.llm_processor and hasattr(self.llm_processor, 'process_image'):
            #     asyncio.create_task(self._analyze_image_async(screenshot_data, device_id, request_id))
        else:
            log.info(f"[{self.extension_id}][Req:{request_id}] No screenshot data received in context.")


        if browser_url and isinstance(browser_url, str) and device_id and request_id:
            log.info(f"[{self.extension_id}][Req:{request_id}] URL detected: {browser_url}. Triggering background processing for device {device_id}.")
            if not self.sse_sender:
                 log.error(f"[{self.extension_id}][Req:{request_id}] Cannot start background task: SSE sender not available.")
                 return CopyResponse(
                    notification_title = f"Internal error",
                    notification_detail = f"SSE not configured. Please check your configuration.",
                    is_processing_task = False
                 )
            else:
                try:
                    asyncio.create_task(
                        self._summarize_url_content_async(browser_url, device_id, request_id)
                    )
                    log.info(f"[{self.extension_id}][Req:{request_id}] Background task created successfully.")
                    # Modify notification based on whether screenshot was also present?
                    detail_msg = "Starting background summarization for URL..."
                    if screenshot_data:
                        detail_msg += " (Screenshot data also received)."

                    return CopyResponse(
                        notification_title = f"Request received",
                        notification_detail = detail_msg,
                        is_processing_task = True
                    )
                except Exception as e:
                     log.error(f"[{self.extension_id}][Req:{request_id}] Failed to create background task: {e}", exc_info=True)
                     return CopyResponse(
                        notification_title = f"Internal error",
                        notification_detail = f"Failed to create background task: {e}",
                        is_processing_task = False
                     )
        elif not browser_url or not isinstance(browser_url, str):
            log.info(f"[{self.extension_id}][Req:{request_id}] No valid 'browser_url' found in window_info: {window_info}")
            return CopyResponse(
                notification_title = f"Request received",
                notification_detail = f"No valid URL found in window_info.",
                is_processing_task = False
            )
        elif not device_id or not request_id:
             log.error(f"[{self.extension_id}] Missing device_id or request_id in context. Cannot start background task. Context keys: {list(context.keys())}")
             return CopyResponse(
                notification_title = f"Internal error",
                notification_detail = f"Missing device_id or request_id in context.",
                is_processing_task = False
             )

        return CopyResponse(
            notification_title = "Request received",
            notification_detail = "No browser URL found to process." + (" Screenshot data received." if screenshot_data else ""),
            is_processing_task = False
        )


    def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        """
        Handles paste events by logging context and returning a response object.
        """
        log.info(f"[{self.extension_id}] on_paste triggered.")
        log.info(f"[{self.extension_id}] Context: {context}")

        paste_content: Optional[str] = None
        notification: Optional[str] = None
        target_app = context.get("target_application")

        if target_app == "MyNoteApp":
            paste_content = f"Pasted from SampleExtension! (API Key Present: {bool(self.api_key)})"
            notification = "Pasting content from SampleExtension."
            log.info(f"[{self.extension_id}] Providing paste content: '{paste_content}'")
        else:
            notification = f"SampleExtension ignored paste in {target_app}."
            log.info(
                f"[{self.extension_id}] Not handling paste for application: {target_app}. "
                f"Paste context keys: {list(context.keys())}"
            )

        return PasteResponse(paste_content=paste_content, notification_message=notification)

    def get_status(self) -> Dict[str, Any]:
        """
        Returns the current status of the extension.
        """
        log.info(f"[{self.extension_id}] get_status called.")
        return {
            "extension_id": self.extension_id,
            "status": "active",
            "config": {"api_key_configured": bool(self.api_key)},
            "version": "1.4.0-summarize", # Updated version example
            "dependencies": ["SSESenderInterface", "LLMProcessorInterface"]
        }

    def shutdown(self) -> None:
        """
        Perform any cleanup needed when the extension is shutting down.
        """
        log.info(f"[{self.extension_id}] Shutting down...")
        # No specific resources to clean up in this example

# To make this discoverable by the framework, often you might need
# a specific variable or function at the module level, e.g.:
# extension_class = SampleExtension
# Or the framework might inspect the module for classes inheriting ExtensionInterface.
