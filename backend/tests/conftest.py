"""Force deterministic offline providers for the automated test suite.

The developer's local backend/.env may contain real API keys. Tests must never
spend quota or depend on network availability, so environment overrides are set
before app.main (and therefore app.config.settings) is imported.
"""

import os

os.environ.update(
    {
        "LLM_PROVIDER": "mock",
        "LLM_MODEL": "grounded-fallback",
        "LLM_API_KEY": "",
        "VISION_PROVIDER": "mock",
        "VISION_MODEL": "local",
        "VISION_API_KEY": "",
        "SPEECH_PROVIDER": "local",
        "WHISPER_MODEL": "base",
        "EMBEDDING_PROVIDER": "hashing_cosine",
    }
)
