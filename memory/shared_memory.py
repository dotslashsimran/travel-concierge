import json
import threading
from datetime import datetime
from typing import Any, Optional
from schemas.output_schemas import (
    FlightOption, HotelOption, Place, DayPlan,
    BudgetOutput, Detection, ImageArtifact, ItineraryOutput
)


class SharedMemory:
    """Central shared memory passed between all CrewAI agents."""

    def __init__(self):
        self._lock = threading.Lock()
        self.userProfile: dict[str, Any] = {}
        self.preferences: dict[str, Any] = {}
        self.selectedFlights: dict[str, Any] = {}
        self.selectedHotel: dict[str, Any] = {}
        self.shortlistedActivities: list[dict[str, Any]] = []
        self.itineraryDraft: list[dict[str, Any]] = []
        self.budgetState: dict[str, Any] = {}
        self.detections: list[dict[str, Any]] = []
        self.reasoningNotes: list[dict[str, Any]] = []
        self.intermediateArtifacts: list[dict[str, Any]] = []
        self._audit_log: list[dict[str, Any]] = []

    def update(self, agent_name: str, key: str, value: Any) -> None:
        with self._lock:
            setattr(self, key, value)
            self._audit_log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent_name,
                "action": "update",
                "key": key,
            })

    def append_to(self, agent_name: str, key: str, item: Any) -> None:
        with self._lock:
            target = getattr(self, key, [])
            if isinstance(target, list):
                target.append(item)
            self._audit_log.append({
                "timestamp": datetime.utcnow().isoformat(),
                "agent": agent_name,
                "action": "append",
                "key": key,
            })

    def add_reasoning_note(self, agent_name: str, note: str, metadata: Optional[dict] = None) -> None:
        self.append_to(agent_name, "reasoningNotes", {
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "note": note,
            "metadata": metadata or {},
        })

    def add_detection(self, detection: dict[str, Any]) -> None:
        self.detections.append({
            **detection,
            "timestamp": datetime.utcnow().isoformat(),
        })

    def attach_artifact(self, agent_name: str, artifact_type: str, payload: Any, label: str = "") -> None:
        self.intermediateArtifacts.append({
            "timestamp": datetime.utcnow().isoformat(),
            "agent": agent_name,
            "type": artifact_type,
            "label": label,
            "payload": payload,
        })

    def to_context_dict(self) -> dict[str, Any]:
        """Serialize memory to a dict for injecting as agent context."""
        with self._lock:
            return {
                "userProfile": self.userProfile,
                "preferences": self.preferences,
                "selectedFlights": self.selectedFlights,
                "selectedHotel": self.selectedHotel,
                "shortlistedActivities": self.shortlistedActivities,
                "itineraryDraft": self.itineraryDraft,
                "budgetState": self.budgetState,
                "detections": self.detections,
                "reasoningNotes": self.reasoningNotes,
            }

    def to_json(self) -> str:
        return json.dumps(self.to_context_dict(), indent=2, default=str)

    def get_audit_log(self) -> list[dict[str, Any]]:
        with self._lock:
            return list(self._audit_log)
