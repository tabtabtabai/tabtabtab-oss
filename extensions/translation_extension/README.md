# Translation Extension

A TabTabTab extension that provides real-time translation capabilities using LLM technology.

## Features

- Translates text to multiple languages
- Supports 10 major languages:
  - English (en)
  - Spanish (es)
  - French (fr)
  - German (de)
  - Italian (it)
  - Portuguese (pt)
  - Russian (ru)
  - Chinese (zh)
  - Japanese (ja)
  - Korean (ko)

## How to Use

1. Copy any text you want to translate
2. The extension will automatically detect the text and start translating it to all supported languages
3. Select the desired translation from the available options
4. Paste the selected translation

## Requirements

- TabTabTab with LLM support
- Internet connection for translation processing

## Implementation Details

The extension uses the following components:

- `ExtensionInterface` for integration with TabTabTab
- LLM processor for translation tasks
- SSE (Server-Sent Events) for real-time updates
- Asynchronous processing for efficient translation handling

## Error Handling

The extension provides clear error messages for various scenarios:

- No text detected for translation
- Translation processing failures
- Network connectivity issues
- Invalid language selections
