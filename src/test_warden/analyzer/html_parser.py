"""HTML parser for DOM tree construction and analysis."""

from dataclasses import dataclass, field
from typing import Iterator

from bs4 import BeautifulSoup, Tag


@dataclass
class DOMElement:
    """Represents a DOM element with all its attributes."""
    
    tag: str
    id: str | None = None
    classes: list[str] = field(default_factory=list)
    text: str | None = None
    attributes: dict[str, str] = field(default_factory=dict)
    xpath: str = ""
    css_selector: str = ""
    parent: "DOMElement | None" = None
    children: list["DOMElement"] = field(default_factory=list)
    
    @property
    def data_testid(self) -> str | None:
        """Get data-testid attribute if present."""
        return self.attributes.get("data-testid")
    
    @property
    def aria_label(self) -> str | None:
        """Get aria-label attribute if present."""
        return self.attributes.get("aria-label")
    
    def matches_selector(self, selector_type: str, selector_value: str) -> bool:
        """Check if this element matches a given selector."""
        if selector_type == "id":
            return self.id == selector_value
        elif selector_type == "class":
            return selector_value in self.classes
        elif selector_type == "data-testid":
            return self.data_testid == selector_value
        elif selector_type == "aria-label":
            return self.aria_label == selector_value
        elif selector_type == "text":
            return self.text and selector_value.lower() in self.text.lower()
        return False


class HTMLParser:
    """Parse HTML and build a navigable DOM tree."""
    
    def __init__(self, html: str):
        self.soup = BeautifulSoup(html, "lxml")
        self._element_cache: dict[str, list[DOMElement]] = {}
    
    def find_by_id(self, element_id: str) -> DOMElement | None:
        """Find element by ID."""
        tag = self.soup.find(id=element_id)
        if tag and isinstance(tag, Tag):
            return self._tag_to_element(tag)
        return None
    
    def find_by_class(self, class_name: str) -> list[DOMElement]:
        """Find all elements with a class."""
        tags = self.soup.find_all(class_=class_name)
        return [self._tag_to_element(t) for t in tags if isinstance(t, Tag)]
    
    def find_by_data_testid(self, testid: str) -> DOMElement | None:
        """Find element by data-testid attribute."""
        tag = self.soup.find(attrs={"data-testid": testid})
        if tag and isinstance(tag, Tag):
            return self._tag_to_element(tag)
        return None
    
    def find_by_aria_label(self, label: str) -> DOMElement | None:
        """Find element by aria-label attribute."""
        tag = self.soup.find(attrs={"aria-label": label})
        if tag and isinstance(tag, Tag):
            return self._tag_to_element(tag)
        return None
    
    def find_by_text(self, text: str, tag_name: str | None = None) -> list[DOMElement]:
        """Find elements containing specific text."""
        results = []
        for tag in self.soup.find_all(tag_name):
            if isinstance(tag, Tag) and tag.string and text.lower() in tag.string.lower():
                results.append(self._tag_to_element(tag))
        return results
    
    def find_by_css(self, css_selector: str) -> list[DOMElement]:
        """Find elements matching a CSS selector."""
        try:
            tags = self.soup.select(css_selector)
            return [self._tag_to_element(t) for t in tags if isinstance(t, Tag)]
        except Exception:
            return []
    
    def all_elements(self) -> Iterator[DOMElement]:
        """Iterate over all elements in the document."""
        for tag in self.soup.find_all(True):
            if isinstance(tag, Tag):
                yield self._tag_to_element(tag)
    
    def _tag_to_element(self, tag: Tag, parent: DOMElement | None = None) -> DOMElement:
        """Convert a BeautifulSoup Tag to a DOMElement."""
        element = DOMElement(
            tag=tag.name,
            id=tag.get("id"),
            classes=tag.get("class", []),
            text=tag.string.strip() if tag.string else None,
            attributes={k: str(v) for k, v in tag.attrs.items() if k not in ("id", "class")},
            xpath=self._generate_xpath(tag),
            css_selector=self._generate_css_selector(tag),
            parent=parent,
        )
        return element
    
    def _generate_xpath(self, tag: Tag) -> str:
        """Generate an XPath for the element."""
        parts = []
        current = tag
        
        while current and current.name != "[document]":
            if current.get("id"):
                parts.insert(0, f'//*[@id="{current.get("id")}"]')
                break
            
            # Count previous siblings of same type
            siblings = [s for s in current.previous_siblings if isinstance(s, Tag) and s.name == current.name]
            index = len(siblings) + 1
            
            if index > 1:
                parts.insert(0, f"{current.name}[{index}]")
            else:
                parts.insert(0, current.name)
            
            current = current.parent  # type: ignore
        
        return "/" + "/".join(parts) if parts else ""
    
    def _generate_css_selector(self, tag: Tag) -> str:
        """Generate a CSS selector for the element."""
        if tag.get("id"):
            return f"#{tag.get('id')}"
        
        if tag.get("data-testid"):
            return f'[data-testid="{tag.get("data-testid")}"]'
        
        classes = tag.get("class", [])
        if classes:
            return f"{tag.name}.{'.'.join(classes[:2])}"  # Limit to 2 classes
        
        return tag.name
