# Notion MCP Extension README

This TabTabTab extension allows you to quickly add copied text to a relevant page in your Notion workspace. It leverages the Model Context Protocol (MCP) to understand the context of the copied text and interact with your Notion via configured tools.

## Dependencies

This extension requires the following dependencies to be configured in TabTabTab:

1.  **`notion_mcp_url`**: The URL of your hosted MCP server that provides Notion tools (specifically tools for searching pages and appending content). You can get a free, hosted MCP server URL from [Gumloop MCP](https://www.gumloop.com/mcp).
2.  **`anthropic_api_key`**: Your API key for the Anthropic API (used for the underlying language model processing).
3.  **Optional: `my_location`**: Your current location might be used by the underlying language model for context, although it's generally less critical for this specific workflow.

## How it Works

The extension listens only for `copy` events within TabTabTab.

### On Copy

-   When you copy text, the extension analyzes it in the background.
-   It sends the copied text to an Anthropic language model with a specific instruction: "I would like to add the following text to my Notion page, search for the page that is relevant to the text, and add the text to the page. If no relevant page is found, pick one page of the available pages and add the text there."
-   The language model uses the tools provided by your configured `notion_mcp_url` (like searching Notion pages and appending content) to fulfill this request.
-   The extension attempts to execute the actions determined by the model via the MCP server.
-   It sends notifications to inform you about the progress ("Processing Notion query", "Calling Notion MCP", "Here's what we found...", or errors).

*(Note: This extension currently does **not** handle `paste` events or arbitrary Notion queries/commands beyond adding the copied text to a page.)*

## Features

-   **Contextual Page Addition:** Attempts to find a relevant Notion page for your copied text and appends the text there.
-   **MCP Integration:** Connects to a standard MCP server for Notion tool execution (search, append).
-   **Asynchronous Processing:** Performs analysis and Notion actions in the background without blocking the UI.
-   **User Notifications:** Keeps you informed about the status of adding content to Notion.
-   **Configurable:** Relies on user-provided dependencies for flexibility.

## Setup

1.  Ensure the extension is enabled in TabTabTab.
2.  Configure the required dependencies (`notion_mcp_url`, `anthropic_api_key`) in the TabTabTab settings. Get your `notion_mcp_url` from [Gumloop MCP](https://www.gumloop.com/mcp). Ensure the MCP server provides tools for searching and appending to Notion pages.
3.  Start copying text you want to add to Notion!
