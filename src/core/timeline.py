import json
from typing import Dict, Any, List

class Timeline:
    def __init__(self, config_path: str = None):
        self.events: List[Dict[str, Any]] = []
        if config_path:
            self.load_from_json(config_path)

    def load_from_json(self, path: str):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.events = sorted(data.get("timeline_events", []), key=lambda e: e.get("frame", 0))

    def get_event_at_frame(self, frame: int) -> Dict[str, Any]:
        last_event = None
        for ev in self.events:
            if ev.get("frame", 0) <= frame:
                last_event = ev
            else:
                break
        return last_event or {}
