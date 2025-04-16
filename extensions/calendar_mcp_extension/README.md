
# Calendar MCP Extension README

This TabTabTab extension allows you to interact with your calendar using natural language. It leverages the Model Context Protocol (MCP) to understand your requests from copied text or paste hints and execute relevant calendar actions or queries.

## Dependencies

This extension requires the following dependencies to be configured in TabTabTab:

1.  **`my_location`**: Your current location (e.g., "Vancouver, BC") to help resolve timezones and location-specific requests.
2.  **`calendar_mcp_url`**: The URL of your hosted MCP server that provides calendar tools (like creating/updating events). You can get a free, hosted MCP server URL from [Gumloop MCP](https://www.gumloop.com/mcp).
3.  **`anthropic_api_key`**: Your API key for the Anthropic API (used for the underlying language model processing).

## How it Works

The extension listens for `copy` and `paste` events within TabTabTab.

### On Copy

-   When you copy text (e.g., "Meeting with John tomorrow at 2 PM", "schedule lunch with Sarah next Tuesday at noon"), the extension analyzes it in the background.
-   It uses an Anthropic language model along with tools provided by your configured `calendar_mcp_url` and a built-in `get_current_time` tool.
-   If the text contains instructions for a calendar action (like creating or updating an event), the extension will attempt to execute it via the MCP server.
-   It sends notifications to inform you about the progress ("Analyzing", "Updated calendar", "Fetched data", or errors).

### On Paste

-   When you trigger a paste action in TabTabTab, the extension receives a "hint" (usually the text preceding the cursor).
-   If the hint contains keywords like "calendar" or "time" (e.g., "what time is it?", "check my calendar for tomorrow"), the extension processes the hint similarly to the `on_copy` flow.
-   It uses the language model and available tools (excluding potentially destructive ones like `create_event` or `update_event` in paste mode) to answer your query or fetch information.
-   The result is provided as a paste suggestion notification ("Fetched data").

## Features

-   **Natural Language Understanding:** Parses plain text to identify calendar-related intents.
-   **MCP Integration:** Connects to a standard MCP server for calendar tool execution.
-   **Time Awareness:** Includes a tool to get the current time in a specified timezone.
-   **Location Context:** Uses your `my_location` dependency to provide context for requests.
-   **Asynchronous Processing:** Performs analysis in the background without blocking the UI.
-   **User Notifications:** Keeps you informed about the status of your requests.
-   **Configurable:** Relies on user-provided dependencies for flexibility.

## Setup

1.  Ensure the extension is enabled in TabTabTab.
2.  Configure the required dependencies (`my_location`, `calendar_mcp_url`, `anthropic_api_key`) in the TabTabTab settings. Get your `calendar_mcp_url` from [Gumloop MCP](https://www.gumloop.com/mcp).
3.  Start copying text or using paste hints related to calendar actions or time queries!
