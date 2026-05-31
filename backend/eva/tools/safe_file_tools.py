from __future__ import annotations

import shutil
from pathlib import Path
from typing import Any

from ..agent.action_model import AgentAction, AgentObservation
from ..agent.checkpoints import CheckpointStore
from ..agent.rollback import rollback_action
from ..agent.verifier import verify_action
from ..security.action_types import ActionType
from ..security.permission_gate import PermissionContext, evaluate_action


SAFE_ROOT = Path(__file__).resolve().parents[3]


def _safe_path(path: str) -> Path:
    target = Path(path).expanduser().resolve()
    home = Path.home().resolve()
    root = SAFE_ROOT.resolve()
    if not (str(target).startswith(str(root)) or str(target).startswith(str(home))):
        raise ValueError("File path is outside the allowed local roots.")
    return target


def file_read_text(path: str) -> dict[str, Any]:
    action = AgentAction("file.read_text", ActionType.PRIVACY_FILE_READ.value, "Read local file", {"path": path}, [ActionType.PRIVACY_FILE_READ.value], privacy_sensitive=True)
    decision = evaluate_action(action, PermissionContext())
    if decision.decision != "allow":
        return {"ok": False, "requires_permission": True, "decision": decision.as_dict()}
    target = _safe_path(path)
    return {"ok": True, "path": str(target), "content": target.read_text(encoding="utf-8", errors="replace")}


def file_write_text(path: str, content: str, confirmed: bool = False) -> dict[str, Any]:
    target = _safe_path(path)
    action = AgentAction(
        "file.write_text",
        ActionType.DESTRUCTIVE_FILE_ACTION.value,
        "Write local text file",
        {"path": str(target), "content": content},
        [ActionType.DESTRUCTIVE_FILE_ACTION.value],
        destructive=True,
        verification={"method": "file_contains", "path": str(target), "text": content},
        rollback={"checkpoint_type": "file_snapshot", "target": str(target)},
    )
    decision = evaluate_action(action, PermissionContext(override_granted=bool(confirmed)))
    if decision.decision != "allow":
        return {"ok": False, "requires_permission": True, "decision": decision.as_dict()}
    checkpoint = CheckpointStore().create_checkpoint(action)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")
    observation = AgentObservation(action.action_id, True, {"path": str(target)}, "Wrote file.")
    verification = verify_action(action, observation)
    if not verification.verified and checkpoint:
        rollback = rollback_action(action, checkpoint)
        return {"ok": False, "checkpoint": checkpoint.as_dict(), "verification": verification.as_dict(), "rollback": rollback.as_dict()}
    return {"ok": True, "path": str(target), "checkpoint": checkpoint.as_dict() if checkpoint else None, "verification": verification.as_dict()}


def file_patch_text(path: str, old: str, new: str, confirmed: bool = False) -> dict[str, Any]:
    target = _safe_path(path)
    current = target.read_text(encoding="utf-8", errors="replace")
    if old not in current:
        return {"ok": False, "error": "old_text_not_found"}
    return file_write_text(str(target), current.replace(old, new, 1), confirmed=confirmed)


def file_copy(src: str, dst: str, confirmed: bool = False) -> dict[str, Any]:
    source = _safe_path(src)
    dest = _safe_path(dst)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, dest)
    return {"ok": True, "src": str(source), "dst": str(dest), "verified": dest.exists()}


def file_move(src: str, dst: str, confirmed: bool = False) -> dict[str, Any]:
    source = _safe_path(src)
    dest = _safe_path(dst)
    action = AgentAction("file.move", ActionType.DESTRUCTIVE_FILE_ACTION.value, "Move local file", {"path": str(source)}, [ActionType.DESTRUCTIVE_FILE_ACTION.value], destructive=True, rollback={"checkpoint_type": "file_snapshot", "target": str(source)})
    decision = evaluate_action(action, PermissionContext(override_granted=bool(confirmed)))
    if decision.decision != "allow":
        return {"ok": False, "requires_permission": True, "decision": decision.as_dict()}
    checkpoint = CheckpointStore().create_checkpoint(action)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(dest))
    return {"ok": True, "src": str(source), "dst": str(dest), "checkpoint": checkpoint.as_dict() if checkpoint else None, "verified": dest.exists()}


def file_delete(path: str, confirmed: bool = False) -> dict[str, Any]:
    target = _safe_path(path)
    action = AgentAction("file.delete", ActionType.DESTRUCTIVE_FILE_ACTION.value, "Delete local file", {"path": str(target)}, [ActionType.DESTRUCTIVE_FILE_ACTION.value], destructive=True, rollback={"checkpoint_type": "file_snapshot", "target": str(target)})
    decision = evaluate_action(action, PermissionContext(override_granted=bool(confirmed)))
    if decision.decision != "allow":
        return {"ok": False, "requires_permission": True, "decision": decision.as_dict()}
    checkpoint = CheckpointStore().create_checkpoint(action)
    target.unlink()
    return {"ok": True, "path": str(target), "checkpoint": checkpoint.as_dict() if checkpoint else None, "verified": not target.exists()}


def file_list_dir(path: str) -> dict[str, Any]:
    target = _safe_path(path)
    return {"ok": True, "path": str(target), "items": [item.name for item in target.iterdir()][:200]}
