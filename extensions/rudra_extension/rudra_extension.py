from typing import Dict, Any, Optional
import aiohttp
import json
import logging
from tabtabtab_lib.extension_interface import (
    ExtensionInterface,
    CopyResponse,
    PasteResponse,
    OnContextResponse,
    Notification,
    NotificationStatus,
)
import anthropic
from urllib.parse import urlparse

logger = logging.getLogger()


class RudraExtension(ExtensionInterface):
    """Smart Link Manager extension that shortens URLs and provides summaries."""

    def __init__(self):
        self.url_mapping = {}

    async def on_context_request(
        self, source_extension_id: str, context_query: Dict[str, Any]
    ) -> OnContextResponse:
        """Return context about the extension's capabilities."""
        session_id = context_query.get("session_id")
        device_id = context_query.get("device_id")
        key = f"{session_id}-{device_id}"
        url_mapping = self.shortened_urls.get(key, False)
        if not url_mapping:
            return None
        context = OnContextResponse.ExtensionContext(
            description="Shortened url for the link",
            context=url_mapping,
        )
        return OnContextResponse(contexts=[context])

    async def on_copy(self, context: Dict[str, Any]) -> CopyResponse:
        """Handle copy event by processing URLs and creating summaries."""

        request_id = context.get("request_id")
        selected_text = context.get("selected_text")
        device_id = context.get("device_id")
        dependencies = context.get("dependencies", {})
        session_id = context.get("session_id")
        
        if not selected_text:
            return None

        # Check if the selected text is a URL
        try:
            parsed_url = urlparse(selected_text)
            if not all([parsed_url.scheme, parsed_url.netloc]):
                return None
        except:
            return None

        short_url = await self._process_url_in_background(
            request_id, selected_text, device_id, dependencies
        )

        key = f"{session_id}-{device_id}"
        self.url_mapping[key] = f"{selected_text} -> {short_url}"

        return CopyResponse(
            notification=Notification(
                request_id=request_id,
                title="Smart Link Manager",
                detail="Processing URL",
                content=short_url,
                status=NotificationStatus.PENDING,
            )
        )

    async def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        """Handle paste event by providing the processed URL with summary."""
        request_id = context.get("request_id")
        device_id = context.get("device_id")
        dependencies = context.get("dependencies", {})

        # Get the stored result from the context
        stored_result = context.get("extensions_context", {}).get("smart_link_result")
        if not stored_result:
            return None

        return PasteResponse(
            paste=Notification(
                request_id=request_id,
                title="Smart Link Manager",
                detail="URL Summary",
                content=stored_result,
                status=NotificationStatus.READY,
            )
        )

    async def _process_url_in_background(
        self,
        request_id: str,
        url: str,
        device_id: str,
        dependencies: Dict[str, Any],
    ) -> str:
        """Process URL in background: shorten it and create summary."""
        try:
            # Get dependencies
            logger.info(f"RudraExtension: _process_url_in_background: {url}")
            bitly_token = dependencies.get("bitly_token")
            anthropic_api_key = dependencies.get("anthropic_api_key")
            logger.info(f"RudraExtension: _process_url_in_background: {url}")
            if not bitly_token or not anthropic_api_key:
                raise ValueError("Missing required API keys")

            # Step 1: Shorten URL using Bitly
            short_url = await self._shorten_url(url, bitly_token)
            logger.info(f"shortened url: {short_url}")
            return short_url

        except Exception as e:
            logger.error(f"Error processing URL: {e}", exc_info=True)
            raise e

    async def _shorten_url(self, url: str, bitly_token: str) -> str:
        """Shorten URL using Bitly API."""
        headers = {
            "Authorization": f"Bearer {bitly_token}",
            "Content-Type": "application/json",
        }
        data = {"long_url": url}

        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://api-ssl.bitly.com/v4/shorten",
                headers=headers,
                json=data,
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["link"]
                else:
                    error_content = await response.text()
                    logger.error(f"Bitly API error: Status {response.status}, Response: {error_content}")
                    raise Exception(f"Bitly API error: {response.status} - {error_content}")

    async def _fetch_page_content(self, url: str) -> str:
        """Fetch and extract text content from a webpage."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    raise Exception(f"Failed to fetch page: {response.status}")

    async def _generate_summary(self, content: str, api_key: str) -> str:
        """Generate summary using Anthropic Claude."""
        client = anthropic.Anthropic(api_key=api_key)
        
        # Take first 2000 characters for summary
        content_preview = content[:2000]
        
        prompt = """You are an AI assistant tasked with summarizing web page content.
        Analyze the provided text context and generate a concise summary.
        If the content covers multiple distinct topics, structure your summary to reflect this.
        You can use bullet points or numbered lists for different topics if appropriate.
        Aim for clarity and brevity, capturing the main points of the text.
        Respond ONLY with the summary text. Do not include introductory phrases like "Here is the summary:".
        """

        response = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": f"Summarize the following content, grouping by topic if applicable:\n\n{content_preview}"}
            ]
        )
        
        return response.content[0].text
