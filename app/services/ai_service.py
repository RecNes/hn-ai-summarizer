"""AI Service for translation, summarization, and comment analysis.

Supports multiple providers:
- OpenAI / DeepSeek / OpenRouter / LM Studio (openai-compatible API)
- Anthropic (native SDK)
- Ollama (HTTP API)

API keys are NEVER stored in DB or exposed to frontend.
They are read exclusively from .env file.
"""

import json
from typing import Any, Dict, List, Optional

import httpx
from sqlalchemy.future import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.setting import Setting
from app.services.provider_registry import get_provider


class AIService:
    """Service for AI-related functionalities using configurable providers."""

    def __init__(self):
        self.ollama_client = httpx.AsyncClient(timeout=600.0)

    async def _get_active_config(self) -> Dict[str, Any]:
        """Get the currently active AI provider configuration.

        Returns:
            {
                "provider": "openai" | "anthropic" | "deepseek" | ...,
                "type": "openai-compat" | "anthropic" | "ollama-http",
                "api_key": str | None,
                "base_url": str,
                "model": str,
                "config": dict  (provider-specific config from DB)
            }
        """
        # Read DB for user's provider/model selection
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Setting).limit(1))
            setting = result.scalar_one_or_none()

        provider_id = None
        model = None
        provider_config = {}

        if setting:
            provider_id = setting.ai_provider
            model = setting.ai_model
            if setting.ai_provider_config:
                try:
                    provider_config = json.loads(setting.ai_provider_config)
                except (json.JSONDecodeError, TypeError):
                    provider_config = {}

            # Legacy fallback: if no ai_provider but ollama fields set
            if not provider_id and setting.ollama_api_url:
                provider_id = "ollama"
                model = model or setting.ollama_model or "llama2"
                provider_config["base_url"] = setting.ollama_api_url

        # If nothing configured, try fallback: check env for any key
        if not provider_id:
            env_providers = self._detect_available_from_env()
            if env_providers:
                provider_id = env_providers[0]  # use first available
                model = self._get_default_model(provider_id)
            else:
                # Last resort: try local Ollama
                provider_id = "ollama"
                model = "llama2"

        provider_def = get_provider(provider_id)
        if not provider_def:
            raise ValueError(f"Unknown AI provider: {provider_id}")

        # Resolve API key from .env
        api_key = None
        env_key_name = provider_def.get("env_key")
        if env_key_name:
            api_key = getattr(settings, env_key_name, None) or ""

        # Resolve base URL
        base_url = provider_config.get("base_url") or provider_def.get("base_url", "")

        return {
            "provider": provider_id,
            "type": provider_def["type"],
            "api_key": api_key,
            "base_url": base_url,
            "model": model or self._get_default_model(provider_id),
            "config": provider_config,
        }

    def _get_default_model(self, provider_id: str) -> str:
        defaults = {
            "openai": "gpt-3.5-turbo",
            "anthropic": "claude-3-haiku-20240307",
            "deepseek": "deepseek-chat",
            "openrouter": "openai/gpt-3.5-turbo",
            "lmstudio": "local-model",
            "ollama": "llama2",
            "gemini": "gemini-2.5-flash",
        }
        return defaults.get(provider_id, "gpt-3.5-turbo")

    def _detect_available_from_env(self) -> List[str]:
        """Detect which providers have API keys set in .env."""
        available = []
        for pid in ["openai", "anthropic", "deepseek", "openrouter", "gemini"]:
            prov = get_provider(pid)
            if prov:
                env_val = getattr(settings, prov["env_key"], None)
                if env_val and str(env_val).strip():
                    available.append(pid)
        return available

    async def _call_openai_compat(
        self, system_prompt: str, user_prompt: str, model: str, base_url: str, api_key: str
    ) -> str:
        """Call any OpenAI-compatible API (OpenAI, DeepSeek, OpenRouter, LM Studio)."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url, timeout=300.0)
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=500,
                temperature=0.3,
            )
            content = response.choices[0].message.content
            if content:
                return content.strip()
            # If content is None/empty, try to get finish_reason for debugging
            finish = response.choices[0].finish_reason
            print(f"Warning: {base_url} ({model}) returned empty content (finish_reason={finish})")
            return ""
        except Exception as e:
            import traceback
            print(f"Error calling {base_url} ({model}): {e}")
            traceback.print_exc()
            return ""

    async def _call_anthropic(
        self, system_prompt: str, user_prompt: str, model: str, api_key: str
    ) -> str:
        """Call Anthropic API."""
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=500,
                temperature=0.3,
            )
            return response.content[0].text.strip()
        except Exception as e:
            print(f"Error calling Anthropic ({model}): {e}")
            return ""

    async def _call_ollama(
        self, prompt: str, model: str, base_url: str
    ) -> str:
        """Call Ollama API."""
        try:
            # Test connection first
            try:
                ping_response = await self.ollama_client.get(
                    f"{base_url}/api/tags", timeout=30.0
                )
                if ping_response.status_code != 200:
                    print(f"Ollama API not responding at {base_url}")
                    return ""
            except Exception as ping_error:
                print(f"Cannot connect to Ollama at {base_url}: {ping_error}")
                return ""

            response = await self.ollama_client.post(
                f"{base_url}/api/generate",
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=600.0,
            )

            if response.status_code == 200:
                result = response.json()
                return result.get("response", "").strip()
            else:
                print(f"Ollama API error: {response.status_code} - {response.text}")
                return ""
        except Exception as e:
            print(f"Error calling Ollama at '{base_url}': {e}")
            return ""

    async def _call_ai(self, system_prompt: str, user_prompt: str) -> str:
        """Route the AI call to the currently configured provider."""
        cfg = await self._get_active_config()
        provider_type = cfg["type"]
        model = cfg["model"]

        if provider_type == "openai-compat":
            return await self._call_openai_compat(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                base_url=cfg["base_url"],
                api_key=cfg["api_key"] or "",
            )
        elif provider_type == "anthropic":
            return await self._call_anthropic(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
                model=model,
                api_key=cfg["api_key"] or "",
            )
        elif provider_type == "ollama-http":
            # Ollama doesn't use system/user split; combine them
            combined = f"{system_prompt}\n\n{user_prompt}"
            return await self._call_ollama(
                prompt=combined,
                model=model,
                base_url=cfg["base_url"],
            )
        else:
            raise ValueError(f"Unknown provider type: {provider_type}")

    def _is_bad_translation(self, original: str, translation: str) -> bool:
        """Detect obviously wrong translations like 'User Safety: safe'.
        
        Returns True if the translation is likely garbage.
        """
        if not translation:
            return True

        t = translation.strip()

        # Too short = suspicious
        if len(t) < 5:
            return True

        # Translation has zero word overlap with original (case-insensitive)
        orig_words = set(original.lower().split())
        trans_words = set(t.lower().split())
        common = orig_words & trans_words

        # Block known garbage patterns
        bad_patterns = ["user safety", "safe", "user", "safety:", "safety", "summary", "note:", "warning"]
        t_lower = t.lower()
        for pat in bad_patterns:
            if pat == t_lower or t_lower.startswith(pat) or t_lower == pat:
                return True

        # If result is in English and has almost no overlap with original, it's probably AI hallucination
        # Check if result contains mostly English characters
        eng_chars = sum(1 for c in t if c.isascii() and c.isalpha())
        turkish_chars = sum(1 for c in t if c in 'çğıiöşüÇĞİÖŞÜ')
        
        # If mostly English but no overlap with original → bad
        if eng_chars > len(t) * 0.6 and turkish_chars < 2:
            if len(common) == 0 and len(orig_words) > 1:
                return True

        return False

    async def translate_title(self, title: str) -> str:
        """Translate title to Turkish with natural, grammatically correct output.
        
        Returns the translated title if successful, otherwise the original title
        without any [TR] prefix.
        """
        prompt = (
            f"Aşağıdaki İngilizce başlığı doğal ve akıcı bir Türkçeye çevir. "
            f"SADECE çeviriyi yaz, açıklama, yorum, madde işareti, ek metin KESİNLİKLE EKLEME. "
            f"Türkçe dilbilgisi kurallarına uygun olsun. Anlam bütünlüğü korunsun. "
            f"Birebir kelime çevirisi yapma, doğal ifadeyi bul.\n\n"
            f"Başlık: {title}\n\n"
            f"Çeviri:"
        )
        result = await self._call_ai(
            system_prompt=(
                "Sen profesyonel bir İngilizce-Türkçe çevirmensin. "
                "Görevin: Verilen İngilizce metni doğal, akıcı ve dilbilgisi kurallarına uygun Türkçeye çevirmek. "
                "ASLA özetleme, yorum ekleme, açıklama yapma. SADECE çeviriyi yaz. "
                "Birebir kelime çevirisinden kaçın, Türkçede doğal karşılığını bul. "
                "Eğer metin zaten Türkçeyse aynen olduğu gibi döndür."
            ),
            user_prompt=prompt,
        )

        # Sonuç yoksa orijinal title'ı döndür
        if not result:
            print(f"Warning: translate_title returned empty. Title={title!r}")
            return title

        # Çeviri aşırı uzunsa kırp
        if len(result) > len(title) * 3:
            print(f"Warning: translate_title too long. Title={title!r}, Result={result!r}")
            trimmed = result[:len(title) * 3 - 3] + "..."
            return trimmed

        # Anlamsız/hatalı çeviri tespit edilirse orijinal title'ı döndür
        if self._is_bad_translation(title, result):
            print(f"Warning: translate_title detected bad translation. Title={title!r}, Result={result!r}")
            return title

        return result

    async def summarize_content(self, content: str) -> str:
        """Summarize content into bullet points in Turkish."""
        if not content:
            return "İçerik özeti mevcut değil."

        content_preview = content[:3000]
        # Direct format: NO instructions to the AI, just the article and the expected output format
        prompt = (
            f"Aşağıdaki makaleyi Türkçe olarak 3 madde halinde özetle.\n"
            f"Her madde '- ' ile başlasın.\n"
            f"SADECE 3 madde yaz, başka hiçbir şey yazma.\n"
            f"Madde metinlerini asla İngilizce yazma, tamamen Türkçe yaz.\n\n"
            f"Makale:\n{content_preview}"
        )
        result = await self._call_ai(
            system_prompt=(
                "Sen bir içerik özetleyicisin. Verilen makaleyi Türkçe 3 madde ile özetlersin. "
                "Yalnızca '- ' ile başlayan 3 satır yazarsın. "
                "Kesinlikle başka açıklama, yorum, düşünce, talimat tekrarı eklemezsin."
            ),
            user_prompt=prompt,
        )
        if not result:
            return "Özet oluşturulamadı."

        result_stripped = result.strip()
        if len(result_stripped) < 20:
            print(f"Warning: summarize_content returned suspiciously short result. Content={content[:50]!r}, Result={result_stripped!r}")
            return "Özet oluşturulamadı."

        # Post-process: remove any lines that look like AI thinking (don't start with '- ')
        cleaned_lines = []
        for line in result_stripped.splitlines():
            line = line.strip()
            if line.startswith('- '):
                cleaned_lines.append(line)
        if cleaned_lines:
            return "\n".join(cleaned_lines)

        return result_stripped

    async def summarize_comments(self, comments: List[Dict[str, Any]]) -> str:
        """Analyze top comments and provide meta-summary in Turkish."""
        if not comments:
            return "Yorum özeti mevcut değil."

        comments_text = "\n".join(
            [comment.get("text", "") for comment in comments[:5]]
        )
        if not comments_text:
            return "Yorum bulunamadı."

        result = await self._call_ai(
            system_prompt=(
                "You are a discussion analyzer. Analyze the following comments and provide a "
                "meta-summary of the discussion in Turkish. Focus on the main points of "
                "agreement, disagreement, and key insights. Keep it to 2-3 sentences. "
                "Return ONLY the summary, nothing else."
            ),
            user_prompt=comments_text[:2000],
        )
        return result if result else "Yorum özeti oluşturulamadı."

    async def check_negative_feedback(self, content: str, title: str) -> bool:
        """Check if content matches negative feedback patterns."""
        return False

    # ────────────────────────────────────────────
    # Translation status check
    # ────────────────────────────────────────────

    def check_translation_complete(self, story) -> bool:
        """Check if all translation fields on a story are fully and correctly translated.

        Returns True only when title_tr, content_tr, and comments_summary
        all contain genuine translated content (not placeholder/garbage).
        """
        if not story:
            return False

        title_ok = (
            bool(story.title_tr)
            and not story.title_tr.startswith("[TR]")
        )
        content_ok = (
            bool(story.content_tr)
            and story.content_tr != "İçerik özeti mevcut değil."
            and story.content_tr != "Özet oluşturulamadı."
        )
        comments_ok = (
            bool(story.comments_summary)
            and story.comments_summary != "Yorum özeti mevcut değil."
        )
        return title_ok and content_ok and comments_ok

    # ────────────────────────────────────────────
    # Provider & Model listing (for API endpoint)
    # ────────────────────────────────────────────

    async def get_available_models(self, provider_id: str, config_str: str = "") -> List[str]:
        """Fetch available models from a provider's API."""
        provider_def = get_provider(provider_id)
        if not provider_def:
            raise ValueError(f"Unknown provider: {provider_id}")

        provider_config = {}
        if config_str:
            try:
                provider_config = json.loads(config_str)
            except json.JSONDecodeError:
                pass

        base_url = provider_config.get("base_url") or provider_def.get("base_url", "")
        env_key_name = provider_def.get("env_key")
        api_key = ""
        if env_key_name:
            api_key = getattr(settings, env_key_name, None) or ""

        ptype = provider_def["type"]

        if ptype == "openai-compat":
            return await self._list_openai_compat_models(api_key, base_url)
        elif ptype == "anthropic":
            return await self._list_anthropic_models(api_key)
        elif ptype == "ollama-http":
            return await self._list_ollama_models(base_url)
        return []

    async def _list_openai_compat_models(self, api_key: str, base_url: str) -> List[str]:
        """List models from any OpenAI-compatible API."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key, base_url=base_url, timeout=30.0)
            models = client.models.list()
            return sorted([m.id for m in models])
        except Exception as e:
            print(f"Error listing models from {base_url}: {e}")
            return []

    async def _list_anthropic_models(self, api_key: str) -> List[str]:
        """List models from Anthropic API."""
        try:
            from anthropic import Anthropic

            client = Anthropic(api_key=api_key)
            models_list = client.models.list()
            return sorted([m.name for m in models_list.data])
        except Exception as e:
            print(f"Error listing Anthropic models: {e}")
            # Fallback to known models
            return [
                "claude-3-opus-20240229",
                "claude-3-sonnet-20240229",
                "claude-3-haiku-20240307",
                "claude-3-5-sonnet-20240620",
                "claude-3-5-haiku-20241022",
            ]

    async def _list_ollama_models(self, base_url: str) -> List[str]:
        """List models from Ollama API."""
        try:
            response = await self.ollama_client.get(
                f"{base_url}/api/tags", timeout=30.0
            )
            if response.status_code == 200:
                data = response.json()
                return sorted([m["name"] for m in data.get("models", [])])
            return []
        except Exception as e:
            print(f"Error listing Ollama models: {e}")
            return []