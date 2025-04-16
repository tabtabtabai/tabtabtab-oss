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
from extensions.mcp_extension_lib import DEFAULT_MODEL, DEFAULT_MAX_TOKENS, DEFAULT_TEMPERATURE
import anthropic

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

# Define tools that might be disabled during paste, if any.
# Example: PASTE_DISABLED_TOOLS = {"create_page", "update_page"}
PASTE_DISABLED_TOOLS = set(["query-database", "list-databases", "create-page"]) # Adjust as needed for Notion tools

class NotionMCPExtension(ExtensionInterface):
    """
    TabTabTab extension that integrates with Notion via MCP (Model Context Protocol)
    """

    # ========== Interface Methods ==========

    async def on_context_request(
        self, source_extension_id: str, context_query: Dict[str, Any]
    ) -> OnContextResponse:
        # Implement if Notion needs context from other extensions
        return None

    async def on_copy(self, context: Dict[str, Any]) -> CopyResponse:
        """
        Process copy events by sending the copied content to the MCP tools for Notion.
        """
        request_id = context.get("request_id")
        selected_text = context.get("selected_text")
        device_id = context.get("device_id")
        dependencies = context.get("dependencies", {}) # Get dependencies here

        logger.info(f"{self.extension_id} on_copy: Text length {len(selected_text) if selected_text else 0}, Request ID: {request_id}")

        if not selected_text:
            logger.warning(f"{self.extension_id}: No text selected for copy (Request ID: {request_id})")
            return None


        # Start background processing, passing dependencies
        logger.info(f"{self.extension_id}: Starting background processing for copy (Request ID: {request_id})")
        asyncio.create_task(
            self._process_in_background(
                request_id, selected_text, device_id, dependencies, mode="copy"
            )
        )

        # Return pending notification immediately
        return CopyResponse(
            notification=Notification(
                request_id=request_id,
                title="Notion",
                detail="Processing Notion query",
                content="Analyzing text for adding to your Notion notes...",
                status=NotificationStatus.PENDING,
            )
        )

    async def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        # We don't provide paste based functionality for Notion
        return None

    async def _process_in_background(
        self,
        request_id: str,
        text: str,
        device_id: str,
        dependencies: Dict[str, Any], # Pass dependencies instead of manager
        mode: str = "copy",
    ) -> None:
        """
        Creates MCPManager, processes text for Notion, and sends notification.
        Handles initialization and cleanup automatically using async with.
        """
        log_prefix = f"{self.extension_id} (Background Task, Request ID: {request_id})"
        logger.info(f"{log_prefix}: Started processing text.")

        final_notification: Notification = None # Define outside try/finally

        # Use async with for automatic setup and teardown of MCPToolProvider
        try:
            # MCPToolProvider handles its own initialization and cleanup via __aenter__/__aexit__
            async with MCPToolProvider() as tool_provider:
                logger.info(f"{log_prefix}: Initializing MCPToolProvider...")
                # Initialization happens within __aenter__
                await tool_provider.initialize(dependencies["mcp_url"])
                logger.info(f"{log_prefix}: MCPToolProvider initialized. Processing text...")

                # Get Anthropic client and tools (MCPToolProvider should provide Notion tools)
                client = anthropic.Anthropic(api_key=dependencies["anthropic_api_key"])

                # Get Notion tools as dictionaries from the provider
                tools_dict = await tool_provider.get_tools_as_dicts([]) # Pass empty list or specific non-Notion tools if needed

                # Filter out paste disabled tools from tools dictionary
                tools_dict = [tool for tool in tools_dict if tool["name"] not in PASTE_DISABLED_TOOLS]

                logger.info(f"{log_prefix}: Tools dictionary: {tools_dict}")


                text = f"""
                Given this text: {text}

                I would like to add the following text to my Notion page,
                search for the page that is relevant to the text, and add the text to the page.
                If no relevant page is found, look for page called Scratchpad and add the text there.
                """

                messages = [
                    {"role": "user", "content": text},
                ]

                while True:
                    # Make a direct call to Anthropic using tools parameter
                    response = client.messages.create(
                        model=DEFAULT_MODEL,
                        max_tokens=DEFAULT_MAX_TOKENS,
                        temperature=DEFAULT_TEMPERATURE,
                        system="You are a helpful assistant specialized in Notion queries and actions. You can use the following tools to interact with Notion.", # Notion-specific system prompt
                        tools=tools_dict,  # Now passing the dictionary format directly
                        messages=messages,
                    )

                    contents = response.content
                    messages.append({"role": "assistant", "content": contents})

                    tool_calls = []
                    for content in contents:
                        if isinstance(content, anthropic.types.ToolUseBlock):
                            tool_use_id = content.id
                            tool_name = content.name
                            tool_args = content.input
                            tool_calls.append((tool_use_id, tool_name, tool_args))
                    
                    # Format tool calls into bullet points
                    tool_calls_summary = []
                    for tool_use_id, tool_name, tool_args in tool_calls:
                        tool_calls_summary.append(f"• {tool_name}: {tool_args}")
                    
                    # Join all tool calls into a single string
                    tool_calls_text = "Calling Notion MCP tools:\n"
                    tool_calls_text += "\n".join(tool_calls_summary)
                    logger.info(f"{log_prefix}: Tool calls executed:\n{tool_calls_text}")
                    await self.send_push_notification(
                        device_id=device_id,
                        notification=Notification(
                            request_id=request_id,
                            title="Notion",
                            detail="Calling Notion MCP",
                            content=tool_calls_text,
                            status=NotificationStatus.PENDING,
                        )
                    )

                    tool_results = await tool_provider.execute_all_tools(contents)

                    if not tool_results:
                        result = contents[0].text
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

                final_notification = Notification(
                    request_id=request_id,
                    title="Notion",
                    detail="Here's what we found in Notion based on your request:",
                    content=final_content,
                    status=NotificationStatus.READY,
                )

        except ValueError as e: # Catch specific init errors like missing keys/URL
             logger.error(f"{log_prefix}: Initialization Error - {e}", exc_info=True)
             final_notification = Notification(
                 request_id=request_id,
                 title="Notion",
                 detail="Initialization Error",
                 content=f"Failed to initialize Notion connection: {str(e)}",
                 status=NotificationStatus.ERROR,
             )
        except Exception as e:
            logger.error(f"{log_prefix}: Error during processing: {e}", exc_info=True)
            # Generic error notification
            final_notification = Notification(
                request_id=request_id,
                title="Notion",
                detail="Processing Error",
                content=f"Error: {str(e)}", # Optionally include error in content
                status=NotificationStatus.ERROR,
            )
        # MCPToolProvider cleanup happens automatically when exiting the `async with` block

        # Send the final notification (either success or error)
        if final_notification:
            logger.info(f"{log_prefix}: Sending final notification (Status: {final_notification.status}).")
            try:
                # Assuming self.send_push_notification exists and is awaitable
                await self.send_push_notification(
                    device_id=device_id,
                    notification=final_notification,
                 )
                logger.info(f"{log_prefix}: Final notification sent successfully.")
            except Exception as e:
                 logger.error(f"{log_prefix}: Failed to send final notification: {e}", exc_info=True)
        else:
            # Should not happen if try/except covers all paths, but log just in case
             logger.error(f"{log_prefix}: Processing finished but no final notification was generated.")


    def is_relevant_text(self, text: str) -> bool:
        # Adjust keywords for Notion relevance
        return text and ("notion" in text.lower() or "note" in text.lower() or "page" in text.lower() or "database" in text.lower())
