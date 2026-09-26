"""检测方法业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

import re
from typing import Any

from app.store import store

MODULE = "method"
REQUIRED_FIELDS = ["方法编号", "方法名称", "标准编号"]
STATUS_ORDER = ["现行有效", "修订中", "已废止", "备选"]
ACTION_RULES = {"启用方法": "现行有效", "废止方法": "已废止", "修订方法": "修订中"}
NEGATIVE_ACTIONS: list[str] = []

# 状态排序只允许在「现行有效」与「备选」之间切换优先级，其余状态保持原有相对顺序
STATUS_SORTS: dict[str, dict[str, int]] = {
    "现行有效优先": {"现行有效": 0, "备选": 1},
    "备选优先": {"备选": 0, "现行有效": 1},
}


def _version_key(value: Any) -> tuple[int, ...]:
    """把 V2.1 这类版本号拆成可比较的数字序列，取不到数字时按 0 处理。"""
    parts = re.findall(r"\d+", str(value or ""))
    return tuple(int(part) for part in parts) or (0,)


class MethodService:
    def _normalize(self, row: dict[str, Any]) -> dict[str, Any]:
        """列表、详情、导出口径统一：展示用的「方法状态」始终与流转状态一致。"""
        row["方法状态"] = row.get("status")
        return row

    def list_entries(
        self,
        *,
        method_code: str | None = None,
        standard_code: str | None = None,
        version: str | None = None,
        status: str | None = None,
        status_sort: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = [self._normalize(row) for row in store.rows(MODULE)]
        if method_code:
            rows = [row for row in rows if method_code in str(row.get("方法编号", ""))]
        if standard_code:
            rows = [row for row in rows if standard_code in str(row.get("标准编号", ""))]
        if version:
            rows = [row for row in rows if version in str(row.get("版本号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        if status_sort in STATUS_SORTS:
            priority = STATUS_SORTS[status_sort]
            rows = sorted(
                rows,
                key=lambda row: (
                    priority.get(str(row.get("status")), 2),
                    str(row.get("方法编号", "")),
                    _version_key(row.get("版本号")),
                ),
            )
        # 每条记录带上同一方法编号的版本数，列表据此决定是否可展开历史版本
        counts: dict[str, int] = {}
        for row in store.rows(MODULE):
            code = str(row.get("方法编号", ""))
            counts[code] = counts.get(code, 0) + 1
        for row in rows:
            row["版本数"] = counts.get(str(row.get("方法编号", "")), 1)
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def list_versions(self, method_code: str) -> list[dict[str, Any]]:
        """同一方法编号的全部历史版本，按版本号从新到旧排列。"""
        rows = [
            self._normalize(row)
            for row in store.rows(MODULE)
            if str(row.get("方法编号", "")) == method_code
        ]
        return sorted(rows, key=lambda row: _version_key(row.get("版本号")), reverse=True)

    def status_stats(self) -> list[dict[str, Any]]:
        """按状态统计方法数量，给台账顶部的卡片用。"""
        rows = store.rows(MODULE)
        return [
            {"label": status, "value": sum(1 for row in rows if row.get("status") == status)}
            for status in STATUS_ORDER
        ]

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        entry = store.find(MODULE, entry_id)
        return self._normalize(entry) if entry is not None else None

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return self._normalize(entry), []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"检测方法 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于检测方法可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return self._normalize(entry), f"检测方法已{action}"
