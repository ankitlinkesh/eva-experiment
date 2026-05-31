from __future__ import annotations

from .action_model import AgentAction, RollbackResult
from .checkpoints import Checkpoint, CheckpointStore


def rollback_action(action: AgentAction, checkpoint: Checkpoint | None) -> RollbackResult:
    if checkpoint is None:
        return RollbackResult(action.action_id, False, False, "No checkpoint available for rollback.", "missing_checkpoint")
    if action.action_type in {"EXTERNAL_MESSAGE_SEND", "EXTERNAL_POST"}:
        return RollbackResult(action.action_id, False, False, "Sent external actions cannot be reliably rolled back.", "not_reversible")
    result = CheckpointStore(path=None, root=None).restore_checkpoint(checkpoint.checkpoint_id)
    if result.error == "checkpoint_not_found" and checkpoint.checkpoint_type == "file_snapshot":
        from pathlib import Path
        import shutil

        snapshot = checkpoint.checkpoint_data.get("snapshot")
        if snapshot and checkpoint.target:
            shutil.copy2(Path(snapshot), Path(checkpoint.target))
            return RollbackResult(action.action_id, True, True, f"Restored {checkpoint.target} from checkpoint.")
    return RollbackResult(action.action_id, result.attempted, result.success, result.summary, result.error)
