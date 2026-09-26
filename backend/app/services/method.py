"""检测方法业务规则：状态流转、字段校验、组合筛选与历史版本分组。"""
from __future__ import annotations

import re
from typing import Any

from app.store import store

MODULE = "method"
REQUIRED_FIELDS = ["方法编号", "方法名称", "标准编号"]
STATUS_ORDER = ["现行有效", "修订中", "已废止", "备选"]
# “现行有效/备选”视图下的排序优先级：现行方法排在备选之前
ACTIVE_STATUSES = ["现行有效", "备选"]
ACTION_RULES = {"启用方法": "现行有效", "废止方法": "已废止", "修订方法": "修订中"}
NEGATIVE_ACTIONS = []

VERSION_FIELDS = ["方法编号", "方法名称", "标准编号", "适用范围", "检出限", "精密度", "版本号", "方法状态"]

_VERSION_TOKEN = re.compile(r"\d+|[^\d\s]")


def _version_key(value: Any) -> tuple[Any, ...]:
    """版本号排序键：数字段按数值比，字母段按文本比；例如 2017 < 2017-B < 2017-R1。"""
    tokens = _VERSION_TOKEN.findall(str(value or ""))
    return tuple((0, int(token)) if token.isdigit() else (1, token) for token in tokens)


def _status_of(row: dict[str, Any]) -> str:
    """方法状态以内部 status 字段为准，避免列表与详情出现两套口径。"""
    return str(row.get("status") or "").strip()


def _serialize(row: dict[str, Any], *, matched: bool) -> dict[str, Any]:
    item: dict[str, Any] = {field: row.get(field) for field in VERSION_FIELDS}
    item["id"] = row.get("id")
    item["方法状态"] = _status_of(row)
    item["matched"] = matched
    return item


class MethodService:
    def list_entries(
        self,
        *,
        method_no: str | None = None,
        standard_no: str | None = None,
        version: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 10,
    ) -> tuple[list[dict[str, Any]], int]:
        """按方法编号/标准编号/版本号组合筛选，再按方法编号聚合成历史版本组。

        - status=None：全部状态，按方法编号正序；
        - status='active'：只保留现行有效与备选，现行优先、备选随后；
        - 其他取值：精确匹配单个状态。
        分页以方法编号分组为单位，组内始终带该编号的全部历史版本，
        命中筛选条件的版本会打 matched 标记，方便前端展开并定位。
        """
        rows = store.rows(MODULE)

        method_no = (method_no or "").strip()
        standard_no = (standard_no or "").strip()
        version = (version or "").strip()
        status = (status or "").strip()

        def matches_filters(row: dict[str, Any]) -> bool:
            if method_no and method_no.upper() not in str(row.get("方法编号", "")).upper():
                return False
            if standard_no and standard_no.upper() not in str(row.get("标准编号", "")).upper():
                return False
            if version and version not in str(row.get("版本号", "")):
                return False
            row_status = _status_of(row)
            if status:
                if status == "active":
                    if row_status not in ACTIVE_STATUSES:
                        return False
                elif row_status != status:
                    return False
            return True

        matched_ids = {id(row) for row in rows if matches_filters(row)}
        # 命中任一筛选条件的方法编号；没有任何筛选条件时全部编号都算命中
        filtering = bool(method_no or standard_no or version or status)
        hit_nos = {
            str(row.get("方法编号", ""))
            for row in rows
            if not filtering or id(row) in matched_ids
        }

        groups_by_no: dict[str, list[dict[str, Any]]] = {}
        for row in rows:
            no = str(row.get("方法编号", ""))
            if no not in hit_nos:
                continue
            groups_by_no.setdefault(no, []).append(row)

        groups: list[dict[str, Any]] = []
        for no, group_rows in groups_by_no.items():
            ordered = sorted(group_rows, key=lambda row: _version_key(row.get("版本号")), reverse=True)
            versions = [_serialize(row, matched=id(row) in matched_ids) for row in ordered]
            head = self._pick_head(ordered, active_only=status == "active")
            groups.append({
                "方法编号": no,
                "head": _serialize(head, matched=id(head) in matched_ids),
                "versions": versions,
                "matchedCount": sum(1 for item in versions if item["matched"]),
            })

        if status == "active":
            rank = {name: index for index, name in enumerate(ACTIVE_STATUSES)}
            groups.sort(key=lambda group: (rank.get(_status_of_group(group), len(rank)), group["方法编号"]))
        else:
            groups.sort(key=lambda group: group["方法编号"])

        total = len(groups)
        page = max(page, 1)
        start = (page - 1) * size
        return groups[start:start + size], total

    def _pick_head(self, rows: list[dict[str, Any]], *, active_only: bool) -> dict[str, Any]:
        """选择分组主版本：现行优先，其次备选、修订中、已废止；同状态下取版本号最新。"""
        priority = {name: index for index, name in enumerate(STATUS_ORDER)}
        candidates = rows
        if active_only:
            candidates = [row for row in rows if _status_of(row) in ACTIVE_STATUSES] or rows
        ordered = sorted(candidates, key=lambda row: _version_key(row.get("版本号")), reverse=True)
        return min(ordered, key=lambda row: priority.get(_status_of(row), len(priority)))

    def stats(self) -> dict[str, int]:
        """台账统计：各状态方法版本数量，供列表页卡片展示。"""
        counts = {name: 0 for name in STATUS_ORDER}
        for row in store.rows(MODULE):
            status = _status_of(row)
            if status in counts:
                counts[status] += 1
        return counts

    def list_versions(self, method_no: str) -> list[dict[str, Any]]:
        """同一方法编号的全部历史版本，版本号新的在前。"""
        rows = [
            row for row in store.rows(MODULE)
            if str(row.get("方法编号", "")) == method_no
        ]
        rows.sort(key=lambda row: _version_key(row.get("版本号")), reverse=True)
        return [_serialize(row, matched=True) for row in rows]

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        row = store.find(MODULE, entry_id)
        if row is None:
            return None
        entry = _serialize(row, matched=True)
        entry["同编号版本"] = [
            version for version in self.list_versions(str(row.get("方法编号", "")))
        ]
        return entry

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
        # 列表口径字段与内部状态保持一致，避免出现占位文本
        entry["方法状态"] = entry["status"]
        rows.append(entry)
        return entry, []

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
        entry["方法状态"] = target
        return entry, f"检测方法已{action}"


def _status_of_group(group: dict[str, Any]) -> str:
    return str(group.get("head", {}).get("方法状态") or "")
