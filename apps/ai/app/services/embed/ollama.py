"""Ollama client for embeddings and text/vision generation."""
import httpx
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OllamaClient:
    def __init__(self):
        self.settings = get_settings()
        self.base_url = self.settings.ollama_base_url

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self.base_url, timeout=120.0)

    async def embed(self, text: str, model: str | None = None) -> list[float]:
        model = model or self.settings.ollama_embed_model
        async with self._client() as client:
            resp = await client.post("/api/embed", json={"model": model, "input": text})
            resp.raise_for_status()
            data = resp.json()
            return data["embeddings"][0]

    async def embed_batch(self, texts: list[str], model: str | None = None) -> list[list[float]]:
        model = model or self.settings.ollama_embed_model
        async with self._client() as client:
            resp = await client.post("/api/embed", json={"model": model, "input": texts})
            resp.raise_for_status()
            return resp.json()["embeddings"]

    async def generate(
        self,
        prompt: str,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> tuple[str, int]:
        """Returns (text, token_count)."""
        model = model or self.settings.ollama_text_model
        payload: dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": temperature},
        }
        if system:
            payload["system"] = system
        async with self._client() as client:
            resp = await client.post("/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["response"], data.get("eval_count", 0)

    async def vision_identify(self, image_bytes: bytes, prompt: str) -> tuple[str, int]:
        """Send image to vision model and return response text."""
        import base64
        model = self.settings.ollama_vision_model
        image_b64 = base64.b64encode(image_bytes).decode()
        payload = {
            "model": model,
            "prompt": prompt,
            "images": [image_b64],
            "stream": False,
            "options": {"temperature": 0.1},
        }
        async with self._client() as client:
            resp = await client.post("/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
        return data["response"], data.get("eval_count", 0)

    async def health_check(self) -> bool:
        try:
            async with self._client() as client:
                resp = await client.get("/api/version")
                return resp.status_code == 200
        except Exception:
            return False
