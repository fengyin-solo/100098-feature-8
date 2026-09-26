"""检测方法接口：维护检测方法，覆盖启用方法、废止方法、修订方法等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.method import STATUS_ORDER, MethodService

router = APIRouter(prefix="/api/method", tags=["检测方法"])

service = MethodService()

LIST_FIELDS = ["方法编号", "方法名称", "标准编号", "适用范围", "检出限", "精密度", "版本号", "方法状态"]
STATUSES = STATUS_ORDER


def _resolve_status(status: str | None) -> str | None:
    """校验状态参数；active 表示只看现行有效与备选。"""
    if not status:
        return None
    if status == "active" or status in STATUS_ORDER:
        return status
    raise HTTPException(
        status_code=400,
        detail=f"方法状态「{status}」不支持，可选：现行有效、修订中、已废止、备选、现行/备选",
    )


@router.get("/stats")
def stats() -> dict[str, int]:
    """各状态方法版本数量，供列表页统计卡片展示。"""
    return service.stats()


@router.get("", response_model=PageResult[dict])
def list_entries(
    method_no: str | None = Query(default=None, alias="methodNo", description="按方法编号模糊检索"),
    standard_no: str | None = Query(default=None, alias="standardNo", description="按标准编号模糊检索"),
    version: str | None = Query(default=None, description="按版本号模糊检索"),
    status: str | None = Query(default=None, description="现行有效/修订中/已废止/备选；active 表示仅现行有效与备选"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1),
) -> PageResult[dict]:
    """按方法编号、标准编号与版本号组合筛选；按方法编号分页，组内带历史版本。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    status_value = _resolve_status(status)
    items, total = service.list_entries(
        method_no=method_no,
        standard_no=standard_no,
        version=version,
        status=status_value,
        page=page,
        size=size,
    )
    return PageResult(items=items, total=total, page=page, size=size)


@router.get("/export")
def export_entries(
    method_no: str | None = Query(default=None, alias="methodNo"),
    standard_no: str | None = Query(default=None, alias="standardNo"),
    version: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """导出检测方法清单：返回当前筛选条件下的全量数据（含历史版本）。"""
    status_value = _resolve_status(status)
    items, total = service.list_entries(
        method_no=method_no,
        standard_no=standard_no,
        version=version,
        status=status_value,
        page=1,
        size=10000,
    )
    return {"module": "method", "total": total, "items": items}


@router.get("/{entry_id}", response_model=dict)
def get_entry(entry_id: int) -> dict:
    """读取单条检测方法明细；不存在时给出可读的错误说明。"""
    entry = service.get_entry(entry_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"检测方法 {entry_id} 不存在或已归档")
    return entry


@router.post("", response_model=ActionResult)
def create_entry(payload: EntryPayload) -> ActionResult:
    """登记一条检测方法，缺字段时说明原因而不是静默丢弃。"""
    entry, missing = service.create_entry(payload.values)
    if missing:
        return ActionResult(ok=False, message=f"缺少必填字段：{'、'.join(missing)}")
    return ActionResult(ok=True, message="检测方法已登记", entry=entry)


@router.post("/{entry_id}/actions", response_model=ActionResult)
def run_action(entry_id: int, payload: EntryPayload) -> ActionResult:
    """对单条检测方法执行启用方法、废止方法、修订方法；不允许的动作会被拦下并说明原因。"""
    action = str(payload.values.get("action") or "").strip()
    entry, message = service.run_action(entry_id, action)
    if entry is None:
        return ActionResult(ok=False, message=message)
    return ActionResult(ok=True, message=message, entry=entry)
