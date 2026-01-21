"""Gemini client for Vision and text analysis with Langfuse tracing."""

import base64
from pathlib import Path

import google.generativeai as genai
from tenacity import retry, stop_after_attempt, wait_exponential

from ..config import Config
from ..tracing import TracingClient, get_tracing


class GeminiClient:
    """Client for Gemini AI API with Vision support and Langfuse tracing."""
    
    def __init__(self, config: Config, tracing: TracingClient | None = None):
        self.config = config
        self.model_name = config.gemini.model
        self._tracing = tracing or get_tracing()
        
        # Configure the API
        genai.configure()  # Uses GOOGLE_API_KEY env var
        
        self.model = genai.GenerativeModel(self.model_name)
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def analyze_screenshot(
        self,
        screenshot_path: Path,
        prompt: str,
    ) -> str:
        """Analyze a screenshot using Gemini Vision."""
        # Read and encode image
        with open(screenshot_path, "rb") as f:
            image_data = base64.b64encode(f.read()).decode("utf-8")
        
        image_part = {
            "mime_type": "image/png",
            "data": image_data,
        }
        
        # Trace the call
        with self._trace("analyze_screenshot") as trace_id:
            response = await self.model.generate_content_async([prompt, image_part])
            result = response.text
            
            self._log_generation(
                trace_id=trace_id,
                name="analyze_screenshot",
                input_data={"prompt": prompt[:200], "image": str(screenshot_path)},
                output_data=result[:500],
            )
            
            return result
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def compare_screenshots(
        self,
        baseline_path: Path,
        current_path: Path,
        prompt: str,
    ) -> str:
        """Compare two screenshots using Gemini Vision."""
        def load_image(path: Path) -> dict:
            with open(path, "rb") as f:
                return {
                    "mime_type": "image/png",
                    "data": base64.b64encode(f.read()).decode("utf-8"),
                }
        
        baseline_part = load_image(baseline_path)
        current_part = load_image(current_path)
        
        with self._trace("compare_screenshots") as trace_id:
            response = await self.model.generate_content_async([
                prompt,
                "Baseline screenshot:",
                baseline_part,
                "Current screenshot:",
                current_part,
            ])
            result = response.text
            
            self._log_generation(
                trace_id=trace_id,
                name="compare_screenshots",
                input_data={
                    "prompt": prompt[:200],
                    "baseline": str(baseline_path),
                    "current": str(current_path),
                },
                output_data=result[:500],
            )
            
            return result
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
    )
    async def classify_failure(
        self,
        failure_description: str,
        html_context: str | None = None,
    ) -> str:
        """Classify a test failure using Gemini."""
        prompt = f"""Analyze this test failure and classify it:

Failure: {failure_description}

{f"HTML Context: {html_context[:2000]}" if html_context else ""}

Respond in JSON format:
{{
    "category": "HEALABLE_SELECTOR" | "HEALABLE_TEXT" | "ACTUAL_BUG" | "FLAKY_TIMING",
    "confidence": 0.0-1.0,
    "reasoning": "explanation",
    "suggested_fix": "if healable, suggest the fix"
}}
"""
        with self._trace("classify_failure") as trace_id:
            response = await self.model.generate_content_async(prompt)
            result = response.text
            
            self._log_generation(
                trace_id=trace_id,
                name="classify_failure",
                input_data={"failure": failure_description[:200]},
                output_data=result[:500],
            )
            
            return result
    
    def _trace(self, name: str):
        """Create a trace context."""
        if self._tracing:
            return self._tracing.trace(f"gemini.{name}")
        
        # Return a no-op context manager
        from contextlib import nullcontext
        return nullcontext(None)
    
    def _log_generation(
        self,
        trace_id: str | None,
        name: str,
        input_data: dict,
        output_data: str,
    ) -> None:
        """Log a generation to Langfuse."""
        if self._tracing:
            self._tracing.generation(
                trace_id=trace_id,
                name=name,
                model=self.model_name,
                input_data=input_data,
                output_data=output_data,
                metadata={"provider": "gemini"},
            )
