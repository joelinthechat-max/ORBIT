from dataclasses import dataclass
from pathlib import Path

@dataclass
class Decision:
    allowed: bool
    approval_required: bool
    reason: str

class SafetyPolicy:
    """Conservative policy gate; destructive and external actions require approval."""
    def assess(self, action: dict) -> Decision:
        kind = action.get("kind", "")
        if kind in {"delete", "shell", "external_send", "purchase", "overwrite"}:
            return Decision(False, True, f"'{kind}' is gated and needs explicit approval")
        if kind == "file_write":
            return Decision(True, False, "write allowed inside ORBIT workspace")
        if kind in {"observe", "verify", "wait", "note"}:
            return Decision(True, False, "low-risk action")
        if kind in {"click", "type", "hotkey"}:
            return Decision(False, True, "computer interaction requires approval in this build")
        return Decision(False, True, "unknown action type is denied by default")

    def approve(self, action: dict, approved: bool) -> Decision:
        if not approved: return Decision(False, False, "user denied action")
        return Decision(True, False, "explicitly approved for this action")

    def safe_path(self, root: Path, rel: str) -> Path:
        root=root.resolve(); target=(root/rel).resolve()
        if target != root and root not in target.parents: raise ValueError("Path escapes workspace")
        return target
