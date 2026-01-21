"""Selector finder - find alternative selectors for missing elements."""

from dataclasses import dataclass

from .html_parser import DOMElement, HTMLParser


@dataclass
class SelectorCandidate:
    """A potential replacement selector."""
    
    strategy: str  # id, data-testid, aria-label, text, css, xpath
    value: str
    confidence: float  # 0.0 - 1.0
    resilience_score: int  # 0 - 100
    element: DOMElement


class SelectorFinder:
    """Find alternative selectors for elements in HTML."""
    
    # Priority order for selector strategies (higher = better)
    STRATEGY_PRIORITY = {
        "data-testid": 100,
        "aria-label": 80,
        "id": 70,  # IDs can change, but still decent
        "text": 60,
        "css-attribute": 50,
        "css-class": 30,
        "xpath": 10,  # Last resort
    }
    
    def __init__(self, html: str):
        self.parser = HTMLParser(html)
    
    def find_alternatives(
        self,
        original_selector_type: str,
        original_selector_value: str,
        element_context: dict | None = None,
    ) -> list[SelectorCandidate]:
        """
        Find alternative selectors for a missing element.
        
        Args:
            original_selector_type: The type of selector that failed (id, class, xpath, etc.)
            original_selector_value: The value that failed
            element_context: Optional hints about the element (tag, text, nearby elements)
        
        Returns:
            List of SelectorCandidate sorted by confidence and resilience
        """
        candidates: list[SelectorCandidate] = []
        context = element_context or {}
        
        # Strategy 1: Look for similar data-testid
        candidates.extend(self._find_by_testid_similarity(original_selector_value, context))
        
        # Strategy 2: Look for elements with matching text
        if expected_text := context.get("expected_text"):
            candidates.extend(self._find_by_text(expected_text, context.get("tag")))
        
        # Strategy 3: Look for elements with aria-label
        candidates.extend(self._find_by_aria(original_selector_value, context))
        
        # Strategy 4: Look for similar IDs
        if original_selector_type == "id":
            candidates.extend(self._find_similar_ids(original_selector_value))
        
        # Strategy 5: Look for similar classes
        if original_selector_type in ("class", "css"):
            candidates.extend(self._find_similar_classes(original_selector_value))
        
        # Sort by confidence then resilience
        candidates.sort(key=lambda c: (c.confidence, c.resilience_score), reverse=True)
        
        return candidates[:5]  # Return top 5
    
    def _find_by_testid_similarity(
        self, 
        original: str, 
        context: dict
    ) -> list[SelectorCandidate]:
        """Find elements with similar data-testid values."""
        candidates = []
        
        for element in self.parser.all_elements():
            if testid := element.data_testid:
                similarity = self._string_similarity(original, testid)
                if similarity > 0.5:
                    candidates.append(SelectorCandidate(
                        strategy="data-testid",
                        value=f'[data-testid="{testid}"]',
                        confidence=similarity,
                        resilience_score=self.STRATEGY_PRIORITY["data-testid"],
                        element=element,
                    ))
        
        return candidates
    
    def _find_by_text(self, text: str, tag: str | None = None) -> list[SelectorCandidate]:
        """Find elements containing specific text."""
        candidates = []
        
        for element in self.parser.find_by_text(text, tag):
            # Prefer buttons, links, labels
            tag_bonus = 0.1 if element.tag in ("button", "a", "label", "h1", "h2") else 0
            
            candidates.append(SelectorCandidate(
                strategy="text",
                value=f'//*[contains(text(), "{text}")]',
                confidence=0.7 + tag_bonus,
                resilience_score=self.STRATEGY_PRIORITY["text"],
                element=element,
            ))
        
        return candidates
    
    def _find_by_aria(self, original: str, context: dict) -> list[SelectorCandidate]:
        """Find elements with aria-label attributes."""
        candidates = []
        
        for element in self.parser.all_elements():
            if aria := element.aria_label:
                similarity = self._string_similarity(original, aria)
                if similarity > 0.4:
                    candidates.append(SelectorCandidate(
                        strategy="aria-label",
                        value=f'[aria-label="{aria}"]',
                        confidence=similarity * 0.9,
                        resilience_score=self.STRATEGY_PRIORITY["aria-label"],
                        element=element,
                    ))
        
        return candidates
    
    def _find_similar_ids(self, original_id: str) -> list[SelectorCandidate]:
        """Find elements with similar ID values."""
        candidates = []
        
        for element in self.parser.all_elements():
            if element.id:
                similarity = self._string_similarity(original_id, element.id)
                if similarity > 0.6:
                    candidates.append(SelectorCandidate(
                        strategy="id",
                        value=f"#{element.id}",
                        confidence=similarity,
                        resilience_score=self.STRATEGY_PRIORITY["id"],
                        element=element,
                    ))
        
        return candidates
    
    def _find_similar_classes(self, original: str) -> list[SelectorCandidate]:
        """Find elements with similar class names."""
        candidates = []
        
        # Extract class names from selector
        original_classes = self._extract_classes(original)
        
        for element in self.parser.all_elements():
            if element.classes:
                # Check for overlap
                overlap = set(original_classes) & set(element.classes)
                if overlap:
                    confidence = len(overlap) / max(len(original_classes), len(element.classes))
                    candidates.append(SelectorCandidate(
                        strategy="css-class",
                        value=f".{'.'.join(element.classes[:2])}",
                        confidence=confidence * 0.8,
                        resilience_score=self.STRATEGY_PRIORITY["css-class"],
                        element=element,
                    ))
        
        return candidates
    
    @staticmethod
    def _string_similarity(s1: str, s2: str) -> float:
        """Calculate string similarity (0.0 - 1.0)."""
        s1, s2 = s1.lower(), s2.lower()
        
        if s1 == s2:
            return 1.0
        
        # Simple Jaccard similarity on character n-grams
        def ngrams(s: str, n: int = 3) -> set:
            return {s[i:i+n] for i in range(len(s) - n + 1)}
        
        ng1, ng2 = ngrams(s1), ngrams(s2)
        if not ng1 or not ng2:
            return 0.0
        
        intersection = len(ng1 & ng2)
        union = len(ng1 | ng2)
        
        return intersection / union if union else 0.0
    
    @staticmethod
    def _extract_classes(selector: str) -> list[str]:
        """Extract class names from a CSS selector."""
        import re
        return re.findall(r'\.([a-zA-Z0-9_-]+)', selector)
