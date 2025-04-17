# Sample Extension README

This extension serves as a demonstration of various features available to TabTabTab extensions, including handling `on_copy`, `on_paste`, and `on_context_request` events, performing background tasks, interacting with external services (fetching URL content), using the built-in LLM processor, and sending notifications back to the user.

## Features Demonstrated

*   **Context Request Handling (`on_context_request`)**: Shows how an extension can respond to context requests from other extensions by providing predefined sample data.
*   **Copy Event Handling (`on_copy`)**:
    *   Extracts information from the `context` object, including `device_id`, `request_id`, `window_info`, `screenshot_data`, and `extensions_context`.
    *   Specifically checks `window_info` for a `browser_url`.
    *   If a `browser_url` is found, it triggers an asynchronous background task (`_summarize_url_content_async`) to process the URL.
    *   Logs the presence and size of `screenshot_data` if available.
    *   Logs any `extensions_context` received.
    *   Sends an initial `PENDING` notification.
*   **Background URL Summarization (`_summarize_url_content_async`)**:
    *   Uses the `aiohttp` library to asynchronously fetch the HTML content of the detected `browser_url`.
    *   If fetching is successful, it uses the injected `llm_processor` (provided by the TabTabTab framework) to summarize the fetched text content using a specified model (e.g., `LLMModel.GEMINI_FLASH`).
    *   Sends the final summary or error messages back to the user via push notifications using the injected `sse_sender`.
*   **Paste Event Handling (`on_paste`)**:
    *   Demonstrates triggering a simple, long-running background task (`_sample_long_running_task`) upon a paste event.
    *   The background task simulates work by waiting for 10 seconds.
    *   Sends `PENDING` and `READY` notifications to track the task's progress.
    *   Logs any `extensions_context` received.
*   **Asynchronous Operations**: Utilizes `asyncio` for background tasks, ensuring the main extension flow remains non-blocking.
*   **Logging**: Implements logging to provide insights into the extension's operations and potential issues.
*   **Notifications**: Uses the `Notification` system to provide feedback to the user about ongoing processes and results (Pending, Ready, Error).

## How it Works

1.  **On Copy**: When the user copies something, if the context includes a browser URL, the extension starts fetching and summarizing that URL's content in the background. It immediately returns a "Pending" notification. The summary result is sent later via a push notification. It also logs if a screenshot was part of the context.
2.  **On Paste**: When the user initiates a paste action, the extension starts a dummy background task that waits for 10 seconds and then sends a "Ready" notification. It also logs context received from other extensions.
3.  **On Context Request**: If another extension requests context from this sample extension, it returns predefined static data.

This sample provides a practical example of integrating asynchronous web requests, LLM processing, and background tasks within the TabTabTab extension framework.


