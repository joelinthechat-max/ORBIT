from dataclasses import dataclass, asdict
from typing import List
import re

@dataclass
class Step:
    id: int
    title: str
    kind: str
    status: str = "pending"
    detail: str = ""

class Planner:
    """Safe baseline planner. Model-backed planners can implement the same interface."""
    def plan(self, objective: str) -> List[Step]:
        text=objective.strip()
        if not text: raise ValueError("Objective cannot be empty")
        # Narrow, explicit file creation workflow; never infer deletion or shell execution.
        m=re.match(r"(?is)^(?:create|write|save) (?:a )?file named ([\w.-]+) with (?:the )?text:?\s*(.*)$",text)
        if m:
            return [Step(1,"Prepare requested text file","file_write",detail=f"{m.group(1)}\n{m.group(2)}"), Step(2,"Verify file exists and contents","verify")]
        return [Step(1,"Clarify and decompose objective","note",detail="Development mode: no language model configured. Review this objective and add specific, approved actions."), Step(2,"Await user confirmation or model-backed plan","wait")]
    def replan(self, steps: List[Step], observation: str) -> List[Step]:
        # Do not continue stale actions after an unexpected observation.
        pending=[s for s in steps if s.status=="pending"]
        return [Step(1,"Reassess after observation","note",detail=observation), *[Step(i+2,s.title,s.kind,detail=s.detail) for i,s in enumerate(pending)]]
