
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any

from schemas.data_classes.content_type import ContentType



@dataclass
class LangraphState:
    user_query: str
    base_prompt: str
    final_response: str = ""
    current_source_index: int = 0
    error_message: Optional[str] = None
    web_search_results: List[Dict] = field(default_factory=list)
    completed_sources: Set[ContentType] = field(default_factory=set)
    required_sources: List[ContentType] = field(default_factory=list)
    retrieved_documents: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    detected_language: Optional[str] = None  # <-- add this field
