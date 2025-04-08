from enum import Enum, auto
from typing import Optional, Dict, Any, List
from pydantic import BaseModel


class LLMModel(str, Enum):

    # Top Shelf Models
    ANTHROPIC_SONNET = "claude-3-5-sonnet-latest"
    ANTHROPIC_CLAUDE_SONNET_3_7 = "claude-3-7-sonnet-latest"
    GEMINI_FLASH2 = "gemini-2.0-flash"

    # Gemini models
    GEMINI_FLASH = "gemini-1.5-flash"
    GEMINI_PRO = "gemini-1.5-pro"
    GEMINI_PRO2 = "gemini-2.0-pro-exp"
    GEMINI_PRO_2_5 = "gemini-2.5-pro-exp-03-25"
    GEMINI_FLASH2_EXP = "gemini-2.0-flash-exp"
    GEMINI_FLASH_2_IMAGE_GEN = "gemini-2.0-flash-exp-image-generation"

    # Anthropic models
    ANTHROPIC_HAIKU = "claude-3-5-haiku-latest"

    # # Trash Models
    OPENAI_MINI = "gpt-4o-mini"
    OPENAI_FULL = "gpt-4o"

    @property
    def provider(self) -> str:
        if self.value.startswith("gemini"):
            return "gemini"
        elif self.value.startswith("gpt"):
            return "openai"
        elif self.value.startswith("claude"):
            return "anthropic"
        return "unknown"

    @staticmethod
    def top_shelf_models() -> List[str]:
        return [
            LLMModel.ANTHROPIC_SONNET,
            LLMModel.ANTHROPIC_CLAUDE_SONNET_3_7,
            LLMModel.GEMINI_FLASH2,
        ]


class PredictionResponse(BaseModel):
    text: str
    confidence: float
    model_used: str
    metadata: Dict[str, Any]


class ImageGenerationMode(str, Enum):
    """Enum for different modes of image generation."""

    NONE = "none"  # No image generation needed
    NEW = "new"  # Generate a new image
    CROP = "crop"  # Crop from existing image
    MULTI_MODAL = "multi_modal"  # Generate image along with text
