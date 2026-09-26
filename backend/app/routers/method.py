"""检测方法接口：维护检测方法，覆盖启用方法、废止方法、修订方法等动作。"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas import ActionResult, EntryPayload, PageResult
from app.services.method import STATUS_SORTS, MethodService

router = APIRouter(prefix="/api/method", tags=["检测方法"])

service = MethodService()

LIST_FIELDS = ["方法编号", "方法名称", "标准编号", "适用范围", "检出限", "精密度", "版本号", "方法状态"]
STATUSES = ["现行有效", "修订中", "已废止", "备选"]


class MethodPageResult(PageResult[dict]):
    """检测方法列表分页结果，附带各状态的数量统计。"""

    stats: list[dict[str, Any]] = []


@router.get("", response_model=MethodPageResult)
def list_entries(
    method_code: str | None = Query(default=None, description="按方法编号检索"),
    standard_code: str | None = Query(default=None, description="按标准编号检索"),
    version: str | None = Query(default=None, description="按版本号检索"),
    status: str | None = Query(default=None, description="现行有效、修订中、已废止、备选"),
    status_sort: str | None = Query(default=None, description="现行有效优先、备选优先"),
    keyword: str | None = Query(default=None, description="旧版参数，等同方法编号检索"),
    page: int = 1,
    size: int = 20,
) -> MethodPageResult:
    """按方法编号、标准编号、版本号组合过滤检测方法列表；没有数据时返回空页，不报错。"""
    if size > 200:
        raise HTTPException(status_code=400, detail="每页最多 200 条，请缩小分页范围")
    if status_sort and status_sort not in STATUS_SORTS:
        allowed = "、".join(STATUS_SORTS)
        raise HTTPException(status_code=400, detail=f"状态排序只支持：{allowed}")
    if status and status not in STATUSES:
        raise HTTPException(status_code=400, detail=f"方法状态只支持：{'、'.join(STATUSES)}")
    items, total = service.list_entries(
        method_code=method_code or keyword,
        standard_code=standard_code,
        version=version,
        status=status,
        status_sort=status_sort,
        page=page,
        size=size,
    )
    return MethodPageResult(items=items, total=total, page=page, size=size, stats=service.status_stats())


@router.get("/versions", response_model=list[dict])
def list_versions(method_code: str = Query(description="要展开历史版本的方法编号")) -> list[dict]:
    """列出同一方法编号的全部历史版本；编号不存在时返回空列表。"""
    return service.list_versions(method_code)


@router.get("/export")
def export_entries() -> dict[str, Any]:
    """导出检测方法清单：返回当前过滤条件下的全量数据。"""
    items, total = service.list_entries(page=1, size=10000)
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
