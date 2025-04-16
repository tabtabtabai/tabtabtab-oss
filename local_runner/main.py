import asyncio
import logging
from typing import Any, Dict, Optional
import argparse
import os
import sys

# Adjust path to import from the parent directory's 'extensions' folder
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Import the extension you want to test
# Now import relative to the adjusted sys.path
from extensions.notion_mcp_extension.notion_mcp_extension import NotionMCPExtension

# Import necessary types for mocking/context
from tabtabtab_lib.extension_interface import Notification
from tabtabtab_lib.llm_interface import LLMContext, LLMProcessorInterface
from tabtabtab_lib.sse_interface import SSESenderInterface
from tabtabtab_lib.llm import LLMModel
from dotenv import load_dotenv

# Basic logging setup for the runner
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger("local_runner")

load_dotenv()

# --- Mock Implementations ---

class MockSSESender(SSESenderInterface):
    """Mocks the SSE sender to log events instead of sending them."""
    async def send_event(
        self, device_id: str, event_name: str, data: Dict[str, Any]
    ) -> None:
        log.info(f"[Mock SSE Send] To Device: {device_id}, Event Name: {event_name}, Data: {data}")

    # Add the send_push_notification method required by the ExtensionInterface base
    async def send_push_notification(self, device_id: str, notification: Notification) -> None:
        log.info(
            f"[Mock Send Push] To Device: {device_id}, Request ID: {notification.request_id}, "
            f"Status: {notification.status}, Title: {notification.title}, "
            f"Detail: {notification.detail}, Content: '{notification.content[:50]}...'"
        )


class MockLLMProcessor(LLMProcessorInterface):
    """Mocks the LLM Processor Interface."""
    async def process(
        self,
        system_prompt: str,
        message: str,
        contexts: list[LLMContext],
        model: LLMModel,
        stream: bool = False,
        max_output_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        top_k: Optional[int] = None,
    ) -> Optional[str]:
        # The Notion extension uses Anthropic directly, so this mock might not be hit often
        # unless the base class or other parts use it.
        log.warning("[Mock LLM Process] Called.")
        # Raise the exception as per the user's previous edit if direct LLM use is unsupported here
        raise Exception("Sorry, direct LLM processing via this mock is not supported in the local runner for Notion.")




async def main(action: str, dependencies: Dict[str, Any], wait_time_seconds: int = 20):
    """Main function to instantiate and test the NotionMCPExtension."""
    log.info("--- Starting Local Extension Runner ---")
    log.info(f"Action requested: {action}")

    # --- Instantiate the Extension ---
    # Provide mock implementations for injected dependencies
    extension = NotionMCPExtension(
        sse_sender=MockSSESender(),
        llm_processor=MockLLMProcessor(), # Still needed for potential base class usage
        extension_id="notion_mcp_local_test" # Use a specific ID for the test
    )

    # --- Prepare Sample Context Data ---
    # Sample context for on_copy
    copy_context = {
        "device_id": "test_device_123",
        "request_id": "req_copy_abc",
        "session_id": "session-test-123",
        "timestamp": "2025-04-16T05:39:26.128251",
        "window_info": {
            "bundleIdentifier": "com.google.Chrome",
            "appName": "Google Chrome",
            "windowTitle": "Example Domain",
            "windowOwner": "Google Chrome",
            "windowBounds": {},
            "accessibilityData": {}
        },
        "screenshot_provided": True,
        "screenshot_data": b"simulated_screenshot_bytes",
        "is_final_prediction": False,
        "current_clipboard": None,
        "selected_text": "selected text sample for Notion", # Make text slightly more specific
        "extensions_context": {},
        "dependencies": dependencies # Pass the provided dependencies
    }

    # Sample context for on_paste (Notion extension currently ignores this)
    paste_context = {
        "device_id": "test_device_456",
        "request_id": "req_paste_xyz",
        "session_id": "session-test-123",
        "window_info": {
            "bundleIdentifier": "com.google.Chrome",
            "windowOwner": "Google Chrome",
            "appName": "Google Chrome",
            "windowTitle": "TabTabTab - Manage Extensions",
            "windowBounds": {
                "X": 110,
                "Height": 818,
                "Y": 25,
                "Width": 1330
            },
            "accessibilityData": {
                "browser_url": "http://localhost:8000/extensions",
                "url": "http://localhost:8000/extensions"
            }
        },
        "screenshot_provided": True,
        "screenshot_data": b"",
        "content_type": "image",
        "metadata": {
            "window_info": "{\"bundleIdentifier\":\"com.google.Chrome\",\"appName\":\"Google Chrome\"}"
        },
        "hint": "Sample hint text",
        "sticky_hint": None,
        "current_clipboard": None,
        "mode": "async_paste",
        "is_final_prediction": False,
        "extensions_context": { # Example context from another extension
            "SAMPLE_EXTENSION": {
                "contexts": [
                    {"description": "some_context_key", "context": "some_context_value_async"},
                    {"description": "some_other_context_key", "context": "{\"some_nested_key\": \"some_nested_value_async\"}"}
                ]
            }
        },
        "stream": True,
        "dependencies": dependencies # Pass the provided dependencies
    }

    # --- Call Extension Methods based on action ---
    # Note: The Notion extension's background task uses external services (MCP, Anthropic).
    # For true local testing without network calls, you'd need to mock those within
    # the main function or the test setup (e.g., using unittest.mock.patch).
    # The current setup will attempt to make real network calls based on the dependencies.
    if action in ['copy', 'all']:
        log.info("\n--- Testing on_copy ---")
        try:
            copy_response = await extension.on_copy(copy_context)
            log.info(f"on_copy response: {copy_response}")
            log.info("Waiting for background tasks (may involve network calls)...")
            await asyncio.sleep(wait_time_seconds)
        except Exception as e:
            log.error(f"Error during on_copy or its background task: {e}", exc_info=True)

    if action in ['paste', 'all']:
        log.info("\n--- Testing on_paste ---")
        try:
            paste_response = await extension.on_paste(paste_context)
            log.info(f"on_paste response: {paste_response}")
            log.info("Waiting for background tasks (may involve network calls)...")
            await asyncio.sleep(wait_time_seconds)
        except Exception as e:
            log.error(f"Error calling on_paste: {e}", exc_info=True)

    log.info("\n--- Local Extension Runner Finished ---")


if __name__ == "__main__":
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Run local tests for NotionMCPExtension.") # Updated description
    parser.add_argument(
        'action',
        choices=['copy', 'paste', 'all'],
        help="Specify which action to test: 'copy', 'paste', or 'all'."
    )
    args = parser.parse_args()
    # Using the hardcoded values from the previous version for now:
    dependencies = {
        "mcp_url": os.getenv("MCP_NOTION_URL"),
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
    }

    # Check if required dependencies are present
    if not dependencies.get("mcp_url") or not dependencies.get("anthropic_api_key"):
        log.error("Missing required dependencies: mcp_url or anthropic_api_key")
        sys.exit(1)


    # Run the main async function
    # Pass the action and loaded dependencies
    asyncio.run(main(args.action, dependencies=dependencies, wait_time_seconds=20))
