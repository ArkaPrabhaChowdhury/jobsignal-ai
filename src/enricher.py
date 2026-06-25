from __future__ import annotations

import json
import re
import threading
import time
from collections import deque

import httpx

from src.config import get_settings

COMMON_SKILLS = {
    "python",
    "java",
    "javascript",
    "typescript",
    "react",
    "node",
    "sql",
    "aws",
    "docker",
    "kubernetes",
    "llm",
    "nlp",
    "fastapi",
    "scrapy",
    "postgresql",
    "machine learning",
}


class TokenBucket:
    def __init__(self, max_calls_per_minute: int) -> None:
        self.max_calls_per_minute = max_calls_per_minute
        self.calls: deque[float] = deque()
        self.lock = threading.Lock()

    def wait(self) -> None:
        while True:
            with self.lock:
                now = time.monotonic()
                while self.calls and now - self.calls[0] >= 60:
                    self.calls.popleft()
                if len(self.calls) < self.max_calls_per_minute:
                    self.calls.append(now)
                    return
                sleep_for = 60 - (now - self.calls[0])
            time.sleep(max(sleep_for, 0.05))


class GroqEnricher:
    def __init__(self, api_key: str | None = None, model: str | None = None) -> None:
        settings = get_settings()
        self.api_key = settings.groq_api_key if api_key is None else api_key
        self.model = settings.groq_model if model is None else model
        self.bucket = TokenBucket(settings.groq_rpm_limit)

    def enrich_listing(self, description: str) -> tuple[list[str], float]:
        if not self.api_key:
            return self._fallback_enrichment(description)

        prompt = (
            "Extract technical skills from this job description and rate confidence "
            "it is a software engineering role (0.0-1.0). Return ONLY JSON with "
            'keys "skills" and "confidence".'
        )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "You are a job listing analyzer."},
                {"role": "user", "content": f"{prompt}\n\n{description}"},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        self.bucket.wait()
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
            data = json.loads(content)
            skills = [str(skill).strip() for skill in data.get("skills", []) if str(skill).strip()]
            confidence = float(data.get("confidence", 0.0))
            return skills, confidence
        except (httpx.HTTPError, KeyError, ValueError, json.JSONDecodeError):
            return self._fallback_enrichment(description)

    def answer_question(self, question: str, context: str) -> str:
        if not self.api_key:
            return self._fallback_answer(question, context)

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Answer questions only from the supplied hiring context.",
                },
                {
                    "role": "user",
                    "content": f"Question: {question}\n\nContext:\n{context}",
                },
            ],
            "temperature": 0.1,
        }
        self.bucket.wait()
        try:
            with httpx.Client(timeout=30) as client:
                response = client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=payload,
                )
                response.raise_for_status()
                return response.json()["choices"][0]["message"]["content"].strip()
        except httpx.HTTPError:
            return self._fallback_answer(question, context)

    def _fallback_enrichment(self, description: str) -> tuple[list[str], float]:
        lowered = description.lower()
        skills = []
        for skill in COMMON_SKILLS:
            if skill in lowered:
                skills.append(skill.title() if skill.islower() else skill)
        confidence = 0.8 if skills else 0.45
        if re.search(r"\b(engineer|developer|backend|frontend|full stack|software)\b", lowered):
            confidence = max(confidence, 0.75)
        return sorted(set(skills)), confidence

    def _fallback_answer(self, question: str, context: str) -> str:
        del question
        lines = [line.strip("- ") for line in context.splitlines() if line.startswith("- ")]
        if not lines:
            return "No relevant listings were found for the query."
        return "Based on the indexed listings: " + "; ".join(lines[:5])
