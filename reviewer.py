"""
Helper utilities for invoking Claude Sonnet to review a single code snippet.

This module is independent from Streamlit to keep the UI thin and makes it
easy to unit test the code review prompt/logic later if needed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from anthropic import Anthropic, APIError
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

console = Console()

# Load environment variables once when the module is imported.
load_dotenv()


class MissingAPIKeyError(RuntimeError):
    """Raised when we cannot find an Anthropic API key in the environment."""


@dataclass
class ReviewMetadata:
    """Simple structure returned alongside Claude's response."""

    input_tokens: int
    output_tokens: int
    model: str


class CodeReviewService:
    """Small wrapper around Anthropic's Messages API for code reviews."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        resolved_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not resolved_key:
            raise MissingAPIKeyError(
                "ANTHROPIC_API_KEY is not set. Create a .env file or export it before running the reviewer."
            )

        self.client = Anthropic(api_key=resolved_key)
        default_model = "claude-sonnet-4-5-20250929"
        self.model = model or os.getenv("ANTHROPIC_MODEL", default_model)

    def review(
        self, code: str, filename: Optional[str] = None, language: Optional[str] = None, notes: Optional[str] = None
    ) -> Tuple[str, ReviewMetadata]:
        """Send the code to Claude and return the markdown review text and metadata."""
        if not code.strip():
            raise ValueError("No code provided for review.")

        prompt = self._build_prompt(code=code, filename=filename, language=language, notes=notes)
        console.print(Panel.fit("Dispatching code review to Claude 3.5 Sonnet", title="Claude Review"))

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2000,
                temperature=0,
                system=self._system_instructions(),
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
            )
        except APIError as exc:
            console.print(Panel.fit(f"Anthropic API error: {exc}", title="API Error", style="red"))
            raise

        content = response.content[0].text if response.content else "Claude returned an empty response."
        metadata = ReviewMetadata(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=response.model,
        )

        console.print(
            Panel.fit(
                f"Model: {metadata.model}\nInput tokens: {metadata.input_tokens}\nOutput tokens: {metadata.output_tokens}",
                title="Review complete",
                style="green",
            )
        )

        return content, metadata

    def _build_prompt(
        self, *, code: str, filename: Optional[str], language: Optional[str], notes: Optional[str]
    ) -> str:
        """Craft the user-facing prompt for Claude."""
        filename_line = f"Filename: {filename}\n" if filename else ""
        language_line = f"Language: {language}\n" if language else ""
        notes_line = f"Submitter notes: {notes.strip()}\n" if notes else ""

        return (
            "You are reviewing a single code file uploaded by a developer. "
            "Return your feedback in Markdown with:\n"
            "1. A concise summary of the code's intent and overall quality.\n"
            "2. A prioritized list of actionable findings grouped by severity.\n"
            "3. Specific code references (line numbers if available) and concrete suggestions.\n"
            "4. Optional improvement ideas if time allows.\n\n"
            "Only mention what you directly observe and avoid repeating requirements.\n\n"
            f"{filename_line}{language_line}{notes_line}"
            "Code:\n"
            f"```{language or ''}\n{code.strip()}\n```"
        )

    def _system_instructions(self) -> str:
        return (
            "You are a senior software engineer. "
            "Review a single file at a time. Do not use emojis. "
            "Review based on the following metrics: Code accuracy, code optimality, security vulnerabilities, standard coding conventions, code quality. "
            "Format the response consisting of 5 sections for each of these metrics. Split each section into 3 categories: Major issues, Minor issues, What it does well. "
            "Only include the category if something is found in that category, do not list the categpry if nothing was found, like no major issues, or nothing was done well, etc."
        )


def get_reviewer() -> CodeReviewService:
    """Convenience helper for Streamlit to memoize the service."""
    return CodeReviewService()