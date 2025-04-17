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

import anthropic
from extension_constants import EXTENSION_DEPENDENCIES

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)

supported_languages = {
    "en": "English",
    "ja": "Japanese",
    "zh": "Chinese",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "it": "Italian",
    "pt": "Portuguese",
    "ru": "Russian",
    "ko": "Korean",
}


class TranslationExtension(ExtensionInterface):
    """
    TabTabTab extension that provides translation functionality using Anthropic's Claude model.
    """

    async def on_context_request(
        self, source_extension_id: str, context_query: Dict[str, Any]
    ) -> OnContextResponse:
        """
        Provides context about supported languages to other extensions.
        """
        return OnContextResponse(
            contexts=[
                OnContextResponse.ExtensionContext(
                    description="supported_languages",
                    context=str(supported_languages),
                )
            ]
        )

    async def on_copy(self, context: Dict[str, Any]) -> CopyResponse:
        """
        Process copy events by translating the copied text to multiple languages.
        """
        request_id = context.get("request_id")
        selected_text = context.get("selected_text")
        device_id = context.get("device_id")
        dependencies = context.get("dependencies", {})

        logger.info(f"selected_text: {selected_text}")

        logger.info(
            f"{self.extension_id} on_copy: Text length {len(selected_text) if selected_text else 0}, Request ID: {request_id}"
        )

        if not selected_text:
            logger.warning(
                f"{self.extension_id}: No text selected for translation (Request ID: {request_id})"
            )
            return CopyResponse(
                notification=Notification(
                    request_id=request_id,
                    title="Translation",
                    detail="No text selected",
                    content="",
                    status=NotificationStatus.ERROR,
                )
            )

        # Start background processing
        logger.info(
            f"{self.extension_id}: Starting background translation (Request ID: {request_id})"
        )
        asyncio.create_task(
            self._process_translation(
                request_id, selected_text, device_id, dependencies
            )
        )

        return CopyResponse(
            notification=Notification(
                request_id=request_id,
                title="Translation",
                detail="Translating...",
                content="Preparing translations...",
                status=NotificationStatus.PENDING,
            )
        )

    async def on_paste(self, context: Dict[str, Any]) -> PasteResponse:
        """
        Handles paste events by returning the selected translation.
        """
        request_id = context.get("request_id")
        selected_translation = context.get("selected_translation", "")

        if not selected_translation:
            return PasteResponse(
                paste=Notification(
                    request_id=request_id,
                    title="Translation",
                    detail="No translation selected",
                    content="",
                    status=NotificationStatus.ERROR,
                )
            )

        return PasteResponse(
            paste=Notification(
                request_id=request_id,
                title="Translation",
                detail="Translation pasted",
                content=selected_translation,
                status=NotificationStatus.READY,
            )
        )

    async def _process_translation(
        self,
        request_id: str,
        text: str,
        device_id: str,
        dependencies: Dict[str, Any],
    ) -> None:
        """
        Processes the translation in the background using Anthropic's Claude model.
        """
        logger.info(f"{self.extension_id}: Started translation processing.")

        try:
            # Get the API key from dependencies
            anthropic_api_key = dependencies.get(
                EXTENSION_DEPENDENCIES.anthropic_api_key.name, ""
            )

            if not anthropic_api_key:
                raise ValueError("Anthropic API key not found in dependencies")

            # Create translations for each supported language
            translations = {}
            client = anthropic.Anthropic(api_key=anthropic_api_key)

            for lang_code, lang_name in supported_languages.items():
                if lang_code == "en":  # Skip English if the text is already in English
                    continue

                prompt = f"Translate the following text to {lang_name}:\n\n{text}"

                response = client.messages.create(
                    model="claude-3-opus-20240229",
                    max_tokens=1000,
                    temperature=0.0,
                    system="You are a professional translator. Translate the text accurately while preserving the meaning, tone, and style.",
                    messages=[{"role": "user", "content": prompt}],
                )

                if response and response.content:
                    translation_text = response.content[0].text
                    translations[lang_code] = translation_text

            # Send translations via SSE
            if translations:
                await self.send_push_notification(
                    device_id=device_id,
                    notification=Notification(
                        request_id=request_id,
                        title="Translation",
                        detail="Translations ready",
                        content=str(translations),
                        status=NotificationStatus.READY,
                    ),
                )
            else:
                await self.send_push_notification(
                    device_id=device_id,
                    notification=Notification(
                        request_id=request_id,
                        title="Translation",
                        detail="No translations generated",
                        content="",
                        status=NotificationStatus.ERROR,
                    ),
                )

        except Exception as e:
            logger.error(
                f"{self.extension_id}: Error during translation: {e}",
                exc_info=True,
            )
            await self.send_push_notification(
                device_id=device_id,
                notification=Notification(
                    request_id=request_id,
                    title="Translation",
                    detail="Translation failed",
                    content=f"Error: {str(e)}",
                    status=NotificationStatus.ERROR,
                ),
            )
