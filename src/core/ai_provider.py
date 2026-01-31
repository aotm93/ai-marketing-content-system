from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import httpx
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)


class AIProviderInterface(ABC):
    """Base interface for all AI providers"""

    @abstractmethod
    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text completion"""
        pass

    @abstractmethod
    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        **kwargs
    ) -> bytes:
        """Generate image from prompt"""
        pass

    @abstractmethod
    async def get_embeddings(self, text: str, model: Optional[str] = None) -> List[float]:
        """Get text embeddings"""
        pass


class OpenAICompatibleProvider(AIProviderInterface):
    """Provider that supports any OpenAI-compatible API"""

    def __init__(
        self,
        base_url: str,
        api_key: str,
        text_model: str,
        image_model: str,
        name: str = "openai"
    ):
        self.base_url = base_url
        self.api_key = api_key
        self.text_model = text_model
        self.image_model = image_model
        self.name = name
        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Initialized {name} provider with base URL: {base_url}")

    async def generate_text(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """Generate text using OpenAI-compatible API"""
        try:
            model = model or self.text_model
            logger.info(f"Generating text with model: {model}")

            response = self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating text: {e}")
            raise

    async def generate_image(
        self,
        prompt: str,
        model: Optional[str] = None,
        size: str = "1024x1024",
        **kwargs
    ) -> bytes:
        """Generate image using OpenAI-compatible API"""
        try:
            model = model or self.image_model
            logger.info(f"Generating image with model: {model}")

            response = self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                n=1,
                **kwargs
            )

            image_url = response.data[0].url
            async with httpx.AsyncClient() as client:
                img_response = await client.get(image_url)
                return img_response.content
        except Exception as e:
            logger.error(f"Error generating image: {e}")
            raise

    async def get_embeddings(self, text: str, model: Optional[str] = None) -> List[float]:
        """Get text embeddings"""
        try:
            model = model or "text-embedding-ada-002"
            response = self.client.embeddings.create(
                model=model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embeddings: {e}")
            raise


class AIProviderFactory:
    """Factory for creating AI provider instances"""

    @staticmethod
    def create_provider(
        provider_name: str,
        base_url: str,
        api_key: str,
        text_model: str,
        image_model: str
    ) -> AIProviderInterface:
        """Create an AI provider instance"""
        if provider_name in ["openai", "custom", "azure", "yunwu"]:
            return OpenAICompatibleProvider(
                base_url=base_url,
                api_key=api_key,
                text_model=text_model,
                image_model=image_model,
                name=provider_name
            )
        else:
            raise ValueError(f"Unsupported provider: {provider_name}")

    @staticmethod
    def create_from_config(config: Dict[str, Any]) -> AIProviderInterface:
        """Create provider from configuration dictionary"""
        return AIProviderFactory.create_provider(
            provider_name=config.get("name", "openai"),
            base_url=config["base_url"],
            api_key=config["api_key"],
            text_model=config["models"]["text"],
            image_model=config["models"]["image"]
        )
