import asyncio
import logging
from typing import Any, Dict, Optional, Type
import argparse
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from tabtabtab_lib.extension_interface import (
    Notification,
    ExtensionInterface,
    OnContextResponse,
)
from tabtabtab_lib.llm_interface import LLMContext, LLMProcessorInterface
from tabtabtab_lib.sse_interface import SSESenderInterface
from tabtabtab_lib.llm import LLMModel
from dotenv import load_dotenv
from extension_constants import EXTENSION_DEPENDENCIES


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("local_runner")

load_dotenv()


class MockSSESender(SSESenderInterface):
    """Mocks the SSE sender to log events instead of sending them."""

    async def send_event(
        self, device_id: str, event_name: str, data: Dict[str, Any]
    ) -> None:
        log.info(
            f"[Mock SSE Send] To Device: {device_id}, Event Name: {event_name}, Data: {data}"
        )

    # Add the send_push_notification method required by the ExtensionInterface base
    async def send_push_notification(
        self, device_id: str, notification: Notification
    ) -> None:
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
        raise Exception(
            "Sorry, direct LLM processing via this mock is not supported in the local runner for Notion."
        )


# a complete mock context for on_copy
def get_mock_copy_context():
    return {
        "device_id": "test_device_123",
        "request_id": "req_copy_abc",
        "session_id": "session-test-123",
        "timestamp": "2025-04-16T05:39:26.128251",
        "window_info": {
            "bundleIdentifier": "com.google.Chrome",
            "appName": "Google Chrome",
            "windowTitle": "Example Do∫main",
            "windowOwner": "Google Chrome",
            "accessibilityData": {"browser_url": "https://example.com"},
        },
        "screenshot_provided": True,
        "screenshot_data": b"simulated_screenshot_bytes",
        "selected_text": f"selected text sample for on_copy",
        "dependencies": {},
    }


def get_mock_paste_context():
    return {
        "device_id": "test_device_456",
        "request_id": "req_paste_xyz",
        "session_id": "session-test-123",
        "window_info": {
            "bundleIdentifier": "com.google.Chrome",
            "windowOwner": "Google Chrome",
            "appName": "Google Chrome",
            "windowTitle": "TabTabTab - Manage Extensions",
            "accessibilityData": {
                "browser_url": "http://localhost:8000/extensions",
                "url": "http://localhost:8000/extensions",
            },
        },
        "screenshot_provided": True,
        "screenshot_data": b"",
        "content_type": "text",
        "metadata": {
            "window_info": '{"bundleIdentifier":"com.google.Chrome","appName":"Google Chrome"}'
        },
        "hint": f"Sample hint text for paste",
        "extensions_context": {
            "another_extension_id": {  # Example context from another extension
                "contexts": [
                    {
                        "description": "some_context_key",
                        "context": "some_context_value_async",
                    },
                    {
                        "description": "some_other_context_key",
                        "context": '{"some_nested_key": "some_nested_value_async"}',
                    },
                ]
            }
        },
    }


async def main(
    extension_class: Type[ExtensionInterface],
    action: str,
    dependencies: Dict[str, Any],
    wait_time_seconds: int = 20,
):
    """Main function to instantiate and test the specified Extension."""
    extension_name = extension_class.__name__
    log.info(f"--- Starting Local Extension Runner for {extension_name} ---")
    log.info(f"Action requested: {action}")
    log.info(f"Dependencies provided: {list(dependencies.keys())}")

    extension = extension_class(
        sse_sender=MockSSESender(),
        llm_processor=MockLLMProcessor(),
        extension_id=f"{extension_name}_local_test",
    )

    # --- Call Extension Methods based on action ---
    if action in ["copy", "all"]:
        log.info(f"\n--- Testing {extension_name}.on_copy ---")
        copy_context = get_mock_copy_context()
        copy_context["dependencies"] = dependencies
        try:
            copy_response = await extension.on_copy(copy_context)
            log.info(f"on_copy response: {copy_response}")
            log.info("Waiting for background tasks (may involve network calls)...")
            await asyncio.sleep(wait_time_seconds)
        except Exception as e:
            log.error(
                f"Error during on_copy or its background task: {e}", exc_info=True
            )

    if action in ["paste", "all"]:
        log.info(f"\n--- Testing {extension_name}.on_paste ---")
        paste_context = get_mock_paste_context()
        paste_context["dependencies"] = dependencies
        try:
            paste_response = await extension.on_paste(paste_context)
            log.info(f"on_paste response: {paste_response}")
            log.info("Waiting for background tasks (if any from paste)...")
            await asyncio.sleep(wait_time_seconds)
        except Exception as e:
            log.error(
                f"Error calling on_paste or its background task: {e}", exc_info=True
            )

    # --- Add test for on_context_request ---
    if action in ["context", "all"]:
        log.info(f"\n--- Testing {extension_name}.on_context_request ---")
        context_request_context = {
            "source_extension_id": "source_of_the_request",
            "context_query": {
                "query_type": "sample_query",
                "details": "Requesting general context information.",
                "dependencies": dependencies,
            },
        }
        try:
            context_response: Optional[OnContextResponse] = (
                await extension.on_context_request(
                    source_extension_id=context_request_context["source_extension_id"],
                    context_query=context_request_context["context_query"],
                )
            )
            log.info(f"on_context_request response: {context_response}")
            # No background task wait needed typically for context requests
        except Exception as e:
            log.error(f"Error calling on_context_request: {e}", exc_info=True)

    log.info(f"\n--- Local Extension Runner Finished for {extension_name} ---")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run local tests for extensions.")
    parser.add_argument(
        "extension",
        choices=["notion", "translation"],
        help="Specify which extension to test: 'notion' or 'translation'.",
    )
    parser.add_argument(
        "action",
        choices=["copy", "paste", "context", "all"],
        help="Specify which action to test: 'copy', 'paste', 'context', or 'all'.",
    )
    args = parser.parse_args()

    # Load dependencies based on the extension
    if args.extension == "notion":
        dependencies = {
            EXTENSION_DEPENDENCIES.notion_mcp_url.name: os.getenv("NOTION_MCP_URL"),
            EXTENSION_DEPENDENCIES.anthropic_api_key.name: os.getenv(
                "ANTHROPIC_API_KEY"
            ),
        }
        from extensions.notion_mcp_extension.notion_mcp_extension import (
            NotionMCPExtension,
        )

        extension_class = NotionMCPExtension
    else:  # translation
        dependencies = {
            EXTENSION_DEPENDENCIES.anthropic_api_key.name: os.getenv(
                "ANTHROPIC_API_KEY"
            ),
        }
        from extensions.translation_extension.translation_extension import (
            TranslationExtension,
        )

        extension_class = TranslationExtension

    # Check if required dependencies are present
    if not dependencies.get(EXTENSION_DEPENDENCIES.anthropic_api_key.name):
        log.error("Missing required dependency: anthropic_api_key")
        sys.exit(1)

    # Run the main async function
    asyncio.run(
        main(
            extension_class,
            args.action,
            dependencies=dependencies,
            wait_time_seconds=20,
        )
    )
