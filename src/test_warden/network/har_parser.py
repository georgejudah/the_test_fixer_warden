"""HAR log parser for detecting API/network failures."""

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class NetworkRequest:
    """Represents a network request from HAR log."""
    
    url: str
    method: str
    status: int
    status_text: str
    time_ms: float
    request_headers: dict
    response_headers: dict
    
    @property
    def is_error(self) -> bool:
        """Check if this request resulted in an error."""
        return self.status >= 400
    
    @property
    def is_server_error(self) -> bool:
        """Check if this is a 5xx server error."""
        return 500 <= self.status < 600
    
    @property
    def is_slow(self, threshold_ms: float = 5000) -> bool:
        """Check if request was slow."""
        return self.time_ms > threshold_ms


@dataclass
class HARAnalysisResult:
    """Result of HAR log analysis."""
    
    total_requests: int
    failed_requests: list[NetworkRequest]
    slow_requests: list[NetworkRequest]
    api_errors: list[NetworkRequest]
    
    @property
    def has_api_failures(self) -> bool:
        """Check if there are API failures."""
        return len(self.api_errors) > 0
    
    @property
    def primary_failure(self) -> NetworkRequest | None:
        """Get the most likely failure cause."""
        # Prioritize server errors
        server_errors = [r for r in self.api_errors if r.is_server_error]
        if server_errors:
            return server_errors[0]
        
        # Then any API errors
        if self.api_errors:
            return self.api_errors[0]
        
        return None


class HARParser:
    """Parse HAR (HTTP Archive) logs."""
    
    def __init__(self, har_path: Path):
        self.har_path = har_path
        self._data: dict | None = None
    
    def load(self) -> None:
        """Load HAR file."""
        with open(self.har_path) as f:
            self._data = json.load(f)
    
    def analyze(self) -> HARAnalysisResult:
        """Analyze HAR log for failures."""
        if not self._data:
            self.load()
        
        entries = self._data.get("log", {}).get("entries", [])
        requests = []
        
        for entry in entries:
            req = entry.get("request", {})
            res = entry.get("response", {})
            
            requests.append(NetworkRequest(
                url=req.get("url", ""),
                method=req.get("method", "GET"),
                status=res.get("status", 0),
                status_text=res.get("statusText", ""),
                time_ms=entry.get("time", 0),
                request_headers={h["name"]: h["value"] for h in req.get("headers", [])},
                response_headers={h["name"]: h["value"] for h in res.get("headers", [])},
            ))
        
        failed = [r for r in requests if r.is_error]
        slow = [r for r in requests if r.is_slow]
        api_errors = [r for r in requests if r.is_error and self._is_api_request(r)]
        
        return HARAnalysisResult(
            total_requests=len(requests),
            failed_requests=failed,
            slow_requests=slow,
            api_errors=api_errors,
        )
    
    @staticmethod
    def _is_api_request(req: NetworkRequest) -> bool:
        """Check if request is an API call (not static asset)."""
        url = req.url.lower()
        
        # Common API patterns
        if "/api/" in url or "/graphql" in url:
            return True
        
        # Exclude static assets
        static_extensions = (".js", ".css", ".png", ".jpg", ".svg", ".woff", ".ico")
        return not any(url.endswith(ext) for ext in static_extensions)
