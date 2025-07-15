"""
ASTERIX CAT-48 (Monoradar Target Reports) Processor
Legacy wrapper for backward compatibility.
Now uses the consolidated processor for better performance and unified handling.
"""

from asterix_cat48_consolidated import AsterixConsolidatedProcessor
from typing import Dict, List, Any

class AsterixCAT48Processor:
    """
    Legacy CAT-48 processor wrapper that uses the consolidated processor.
    Maintained for backward compatibility.
    """
    
    def __init__(self):
        self.consolidated = AsterixConsolidatedProcessor()
        self.category = 48
        self.category_name = "Monoradar Target Reports"
    
    def process_cat48_message(self, raw_data: bytes) -> List[Dict[str, Any]]:
        """Process CAT-48 message using consolidated processor."""
        return self.consolidated.process_asterix_message(raw_data)
    
    def create_cat48_message(self, targets: List[Dict[str, Any]]) -> bytes:
        """Create CAT-48 message using consolidated processor."""
        return self.consolidated.create_cat48_message(targets)
    
    def get_message_statistics(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get message statistics using consolidated processor."""
        return self.consolidated.get_message_statistics(messages)
