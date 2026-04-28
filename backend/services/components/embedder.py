import os
import httpx
import logging
from typing import List

logger = logging.getLogger(__name__)

class AIEmbedder:
    def __init__(self):
        self.base_url = os.getenv("OPENAI_BASE_URL", "http://host.docker.internal:11434/v1")
        # Ollama's gemma4 or a specific embedding model like mxbai-embed-large
        self.model = os.getenv("EMBEDDING_MODEL", "mxbai-embed-large")

    async def embed(self, text: str) -> List[float]:
        """
        Generates a vector embedding using Ollama.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url.replace('/v1', '/api/embeddings')}",
                    json={
                        "model": self.model,
                        "prompt": text
                    },
                    timeout=30.0
                )
                if response.status_code == 200:
                    return response.json().get("embedding", [])
                else:
                    logger.error(f"Embedding failed: {response.text}")
                    return []
        except Exception as e:
            logger.error(f"Error during embedding: {e}")
            return []

embedder = AIEmbedder()
