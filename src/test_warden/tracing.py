"""Langfuse integration for LLM observability."""

from contextlib import contextmanager
from functools import wraps
from typing import Any, Callable

from langfuse import Langfuse

from .config import Config


class TracingClient:
    """Langfuse tracing client for observability."""
    
    def __init__(self, config: Config):
        self.config = config
        self.enabled = config.langfuse.enabled
        self._client: Langfuse | None = None
        
        if self.enabled:
            self._client = Langfuse(
                public_key=config.langfuse.public_key,
                secret_key=config.langfuse.secret_key,
            )
    
    @contextmanager
    def trace(self, name: str, metadata: dict | None = None):
        """Create a trace context for an operation."""
        if not self.enabled or not self._client:
            yield None
            return
        
        trace = self._client.trace(
            name=name,
            metadata=metadata or {},
        )
        try:
            yield trace
        finally:
            trace.update(status="completed")
    
    def generation(
        self,
        trace_id: str | None,
        name: str,
        model: str,
        input_data: Any,
        output_data: Any,
        metadata: dict | None = None,
        usage: dict | None = None,
    ) -> None:
        """Log a generation (LLM call) to Langfuse."""
        if not self.enabled or not self._client:
            return
        
        self._client.generation(
            trace_id=trace_id,
            name=name,
            model=model,
            input=input_data,
            output=output_data,
            metadata=metadata or {},
            usage=usage,
        )
    
    def span(
        self,
        trace_id: str | None,
        name: str,
        input_data: Any = None,
        output_data: Any = None,
    ) -> None:
        """Log a span (non-LLM operation) to Langfuse."""
        if not self.enabled or not self._client:
            return
        
        self._client.span(
            trace_id=trace_id,
            name=name,
            input=input_data,
            output=output_data,
        )
    
    def flush(self) -> None:
        """Flush pending events to Langfuse."""
        if self._client:
            self._client.flush()


def trace_gemini_call(name: str):
    """Decorator to trace Gemini API calls."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Get tracing client from self if available
            tracing = getattr(self, '_tracing', None)
            
            if not tracing or not tracing.enabled:
                return await func(self, *args, **kwargs)
            
            # Create trace
            with tracing.trace(name) as trace:
                trace_id = trace.id if trace else None
                
                # Capture input
                input_data = {
                    "args": str(args)[:500],
                    "kwargs": {k: str(v)[:200] for k, v in kwargs.items()},
                }
                
                # Call function
                result = await func(self, *args, **kwargs)
                
                # Log generation
                tracing.generation(
                    trace_id=trace_id,
                    name=name,
                    model=self.config.gemini.model,
                    input_data=input_data,
                    output_data=str(result)[:1000],
                    metadata={"function": func.__name__},
                )
                
                return result
        
        return wrapper
    return decorator


# Global tracing instance (initialized by CLI)
_tracing: TracingClient | None = None


def init_tracing(config: Config) -> TracingClient:
    """Initialize global tracing client."""
    global _tracing
    _tracing = TracingClient(config)
    return _tracing


def get_tracing() -> TracingClient | None:
    """Get the global tracing client."""
    return _tracing
