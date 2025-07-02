
from dataclasses import dataclass, field
from typing import List, Optional, Set, Dict, Any

from schemas.data_classes.content_type import ContentType



@dataclass
class LangraphState:
    user_query: str
    base_prompt: str
    required_sources: List[ContentType] = field(default_factory=list)
    completed_sources: Set[ContentType] = field(default_factory=set)
    retrieved_documents: Dict[str, List[Dict[str, Any]]] = field(default_factory=dict)
    final_response: str = ""
    error_message: Optional[str] = None
    current_source_index: int = 0 
