import asyncio
import logging
from typing import Any, Dict

from tabtabtab_lib.extension_interface import (
    ExtensionInterface,
    CopyResponse,
    PasteResponse,
    OnContextResponse,
    Notification,
    NotificationStatus,
)

from extensions.mcp_extension_lib import MCPToolProvider, Tool
from extensions.mcp_extension_lib import (
    DEFAULT_MODEL,
    DEFAULT_MAX_TOKENS,
    DEFAULT_TEMPERATURE,
)
from datetime import datetime
import pytz
import anthropic

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# These constants should be moved to the top level
PASTE_DISABLED_TOOLS = {"create_event", "update_event"}


def get_current_time(timezone: str):
    """Get the current time in the given timezone"""
    tz = pytz.timezone(timezone)
    current_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    logger.info(f"Current time in {timezone}: {current_time}")
    return f"The current time in {timezone} is {current_time}"


class CalendarMCPExtension(ExtensionInterface):
    """
    TabTabTab extension that integrates with your calendar via MCP (Model Context Protocol)
    """

    async def on_context_request(
        self, source_extension_id: str, context_query: Dict[str, Any]
    ) -> OnContextResponse:
        return None

    async def on_copy(self, context: Dict[str, Any]) -> CopyResponse:
        """
        Process copy events by sending the copied content to the MCP tools.
        """
        request_id = context.get("request_id")
        selected_text = context.get("selected_text")
        device_id = context.get("device_id")
        dependencies = context.get("dependencies", {})  # Get dependencies here

        logger.info(
            f"{self.extension_id} on_copy: Text length {len(selected_text) if selected_text else 0}, Request ID: {request_id}"
        )

        if not selected_text:
            logger.warning(
                f"{self.extension_id}: No text selected for copy (Request ID: {request_id})"
            )
            # Return None or a specific "nothing to do" notification if desired
            return None

        # Start background processing, passing dependencies
        logger.info(
            f"{self.extension_id}: Starting background processing for copy (Request ID: {request_id})"
        )
        asyncio.create_task(
            self._process_in_background(
                request_id, selected_text, device_id, dependencies, mode="copy"
            )
        )

        # Return pending notification immediately
        return CopyResponse(
            notification=Notification(
                request_id=request_id,
                title="Calendar",  # Adjusted title
                detail="Analyzing",
                content="Looking for calendar actions...",
                status=NotificationStatus.PENDING,
            ),
        )

    async def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        """
        Handles paste events by retrieving processed content from the MCP tools.
        """
        hint = context.get("hint")
        request_id = context.get("request_id")
        device_id = context.get("device_id")
        dependencies = context.get("dependencies", {})  # Get dependencies here

        logger.info(
            f"{self.extension_id} on_paste: Hint '{hint}', Request ID: {request_id}"
        )

        if not self.is_relevant_text(hint):
            logger.debug(
                f"{self.extension_id}: Paste hint not relevant (Request ID: {request_id})"
            )
            return None  # Not relevant

        # Start background processing for paste hint
        logger.info(
            f"{self.extension_id}: Starting background processing for paste (Request ID: {request_id})"
        )
        asyncio.create_task(
            self._process_in_background(
                request_id, hint, device_id, dependencies, mode="paste"
            )
        )

        return PasteResponse(
            paste=Notification(
                request_id=request_id,
                title="Calendar",  # Adjusted title
                detail="Processing",
                content="Analyzing text for calendar actions...",
                status=NotificationStatus.PENDING,
            ),
        )

    async def _process_in_background(
        self,
        request_id: str,
        text: str,
        device_id: str,
        dependencies: Dict[str, Any],
        mode: str = "copy",
    ) -> None:
        """
        Creates MCPToolProvider, processes text, and sends notification within this task.
        Handles initialization and cleanup automatically using async with.
        """
        logger.info(f"{self.extension_id}: Started processing text.")

        final_notification = None  # No need for type annotation
        time_tool = Tool.from_function(get_current_time)

        # Extract these values once at the beginning
        my_location = dependencies.get("my_location", "")
        mcp_url = dependencies.get("mcp_url", "")
        anthropic_api_key = dependencies.get("anthropic_api_key", "")

        # The rest of the method can be simplified...
        try:
            async with MCPToolProvider() as tool_provider:
                logger.info(f"{self.extension_id}: Initializing MCPToolProvider...")
                await tool_provider.initialize(mcp_url, [time_tool], "calendar")

                # This block can be simplified - no need for multi-line f-string
                text = f"I am currently at {my_location}. Please resolving the following request: {text}"
                system_prompt = "You are a helpful assistant specialized in calendar and time-related queries. You can use the following tools to help the user."

                client = anthropic.Anthropic(api_key=anthropic_api_key)
                tools_dict = await tool_provider.get_tools_as_dicts()

                if mode == "paste":
                    tools_dict = [
                        tool
                        for tool in tools_dict
                        if tool["name"] not in PASTE_DISABLED_TOOLS
                    ]

                messages = [{"role": "user", "content": text}]
                tool_calls = False

                while True:
                    # Make a direct call to Anthropic using tools parameter
                    response = client.messages.create(
                        model=DEFAULT_MODEL,
                        max_tokens=DEFAULT_MAX_TOKENS,
                        temperature=DEFAULT_TEMPERATURE,
                        system=system_prompt,
                        tools=tools_dict,  # Now passing the dictionary format directly
                        messages=messages,
                    )

                    content = response.content
                    messages.append({"role": "assistant", "content": content})

                    tool_results = await tool_provider.execute_all_tools(content)
                    tool_calls = bool(tool_results)

                    if not tool_results:
                        result = content[0].text
                        break

                    messages.append(
                        {
                            "role": "user",
                            "content": tool_results,
                        }
                    )

                # Process the text
                final_content = result
                logger.info(f"{self.extension_id}: Final content: {final_content}")

                # Determine notification based on mode and result
                title = "Calendar"
                if mode == "copy":
                    # Check if a tool was actually called (implies an action was taken)
                    if tool_calls:
                        detail = "Updated calendar"
                        status = NotificationStatus.READY
                    else:
                        # If no tool was called, LLM might just be responding conversationally
                        detail = "Fetched data"
                        status = NotificationStatus.READY
                else:  # mode == "paste"
                    detail = "Fetched data"
                    status = NotificationStatus.READY

                final_notification = Notification(
                    request_id=request_id,
                    title=title,
                    detail=detail,
                    content=final_content,
                    status=status,
                )

        except ValueError as e:  # Catch specific init errors like missing keys/URL
            logger.error(
                f"{self.extension_id}: Initialization Error - {e}", exc_info=True
            )
            final_notification = Notification(
                request_id=request_id,
                title="Initialization Error",
                detail=f"Failed to initialize calendar connection: {str(e)}",
                content="",
                status=NotificationStatus.ERROR,
            )
        except Exception as e:
            logger.error(
                f"{self.extension_id}: Error during processing: {e}", exc_info=True
            )
            # Generic error notification
            final_notification = Notification(
                request_id=request_id,
                title="Calendar Processing Error",
                detail="An unexpected error occurred while handling your calendar request.",
                content=f"Error: {str(e)}",  # Optionally include error in content
                status=NotificationStatus.ERROR,
            )
        # MCPManager cleanup happens automatically when exiting the `async with` block

        # Send the final notification (either success or error)
        if final_notification:
            logger.info(
                f"{self.extension_id}: Sending final notification (Status: {final_notification.status})."
            )
            try:
                # Assuming self.send_push_notification exists and is awaitable
                await self.send_push_notification(
                    device_id=device_id,
                    notification=final_notification,
                )
                logger.info(
                    f"{self.extension_id}: Final notification sent successfully."
                )
            except Exception as e:
                logger.error(
                    f"{self.extension_id}: Failed to send final notification: {e}",
                    exc_info=True,
                )
        else:
            # Should not happen if try/except covers all paths, but log just in case
            logger.error(
                f"{self.extension_id}: Processing finished but no final notification was generated."
            )

    def is_relevant_text(self, text: str) -> bool:
        # Keep this simple or make it more sophisticated if needed
        return text and ("calendar" in text.lower() or "time" in text.lower())
