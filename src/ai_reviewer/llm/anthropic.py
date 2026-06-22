from __future__ import annotations

import json
from typing import Any

from anthropic import AsyncAnthropic

from ai_reviewer.analysis.categorizer import categorize_findings
from ai_reviewer.analysis.prompts import FINDINGS_TOOL, build_batch_prompt, build_system_prompt
from ai_reviewer.config import ReviewerConfig
from ai_reviewer.models import DiffFile, DiffHunk, Finding


class AnthropicClient:
    def __init__(self, api_key: str, config: ReviewerConfig) -> None:
        self.config = config
        self._client = AsyncAnthropic(api_key=api_key)
        self._system_prompt = build_system_prompt(config)

    async def analyze_hunks(self, file: DiffFile, hunks: list[DiffHunk]) -> list[Finding]:
        user_prompt = build_batch_prompt(file, hunks)
        response = await self._client.messages.create(
            model=self.config.model,
            max_tokens=2048,
            system=self._system_prompt,
            tools=[FINDINGS_TOOL],
            tool_choice={"type": "tool", "name": "report_findings"},
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_findings = self._extract_findings(response)
        return categorize_findings(raw_findings, self.config)

    def _extract_findings(self, response: Any) -> list[dict[str, Any]]:
        for block in response.content:
            if block.type == "tool_use" and block.name == "report_findings":
                input_data = block.input
                if isinstance(input_data, dict):
                    findings = input_data.get("findings", [])
                    if isinstance(findings, list):
                        return findings
                if isinstance(input_data, str):
                    try:
                        parsed = json.loads(input_data)
                        return parsed.get("findings", [])
                    except json.JSONDecodeError:
                        return []
        return []
