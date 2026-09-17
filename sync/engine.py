"""P0 只读镜像：同步引擎。

单进程串行执行，每表独立记录游标与结果；单表失败不影响其他表。只调用读取类接口（api.output / api.fieldinfo）。
"""

from __future__ import annotations

import datetime as dt
import logging
import time
from typing import Any, Dict, Iterable, List, Optional, Set

from xtools import XTools, XToolsError

from .specs import DICT_FIELDS, FIELD_NAME_TABLES, SPEC_BY_DT, TABLE_SPECS, TableSpec
from .store import Store, now_iso, record_id

logger = logging.getLogger("xtools.sync")

LASTTIME_OVERLAP = dt.timedelta(minutes=30)
TIME_FMT = "%Y-%m-%d %H:%M:%S"


class Syncer:
    def __init__(self, xt: XTools, store: Store):
        self.xt = xt
        self.store = store

    # ------------------------------------------------------------------ 公共入口
    def run(self, mode: str = "incremental", tables: Optional[Iterable[str]] = None) -> List[Dict[str, Any]]:
        """mode：init（全量）/ incremental（增量）/ full（强制全量，含删除检测）。返回每表结果。"""
        specs = [SPEC_BY_DT[t] for t in tables] if tables else TABLE_SPECS
        results = []
        for spec in specs:
            results.append(self.sync_table(spec, mode))
        return results

    def sync_table(self, spec: TableSpec, mode: str) -> Dict[str, Any]:
        started = now_iso()
        t0 = time.time()
        state = self.store.get_state(spec.dt)
        result: Dict[str, Any] = {"dt": spec.dt, "table": spec.table, "mode": mode, "rows": 0, "inserted": 0, "updated": 0, "deleted": 0, "status": "ok", "error": None}
        try:
            do_full = mode in ("init", "full") or state["last_full_at"] is None or spec.mode == "full"
            if not do_full and spec.full_every_hours:
                last_full = dt.datetime.fromisoformat(state["last_full_at"])
                if dt.datetime.now() - last_full > dt.timedelta(hours=spec.full_every_hours):
                    do_full = True
            if do_full:
                self._full_pull(spec, state, result, detect_deleted=True)
            elif spec.mode == "lasttime":
                self._lasttime_pull(spec, state, result)
            else:
                self._lastid_pull(spec, state, result)
                for make_params in spec.refresh_params:
                    self._filtered_pull(spec, make_params(), result)
            result["seconds"] = round(time.time() - t0, 1)
            self.store.set_state(spec.dt, last_run_at=now_iso(), last_status="ok", last_rows=result["rows"], last_error=None)
            logger.info("%-16s %-11s 读取 %5d 条：新增 %d 更新 %d 删除 %d（%.1fs）", spec.dt, "全量" if do_full else "增量",
                        result["rows"], result["inserted"], result["updated"], result["deleted"], result["seconds"])
        except Exception as exc:  # 接口错误或数据形态异常：记录后继续下一张表
            result["status"] = "skipped" if (spec.optional and isinstance(exc, XToolsError)) else "error"
            result["error"] = f"{type(exc).__name__}: {exc}"
            result["seconds"] = round(time.time() - t0, 1)
            self.store.set_state(spec.dt, last_run_at=now_iso(), last_status=result["status"], last_error=result["error"])
            (logger.warning if result["status"] == "skipped" else logger.error)("%-16s %s：%s", spec.dt, "跳过（可选表）" if result["status"] == "skipped" else "失败", result["error"])
        self.store.log_run(started_at=started, finished_at=now_iso(), mode=mode, dt=spec.dt, rows=result["rows"],
                           inserted=result["inserted"], updated=result["updated"], deleted=result["deleted"],
                           status=result["status"], error=result["error"])
        return result

    # ------------------------------------------------------------------ 拉取方式
    def _read_params(self, spec: TableSpec) -> Dict[str, Any]:
        params = dict(spec.params)
        if spec.extend is not None:
            params["extend"] = spec.extend
        return params

    def _ingest(self, spec: TableSpec, rows: Iterable[Dict[str, Any]], result: Dict[str, Any]) -> Set[int]:
        """分批写入原始表与规范化表，返回本次见到的 id 集合。"""
        seen: Set[int] = set()
        batch: List[Dict[str, Any]] = []
        for rec in rows:
            rid = record_id(rec)
            if rid is None:
                continue
            seen.add(rid)
            batch.append(rec)
            if len(batch) >= 200:
                self._flush(spec, batch, result)
                batch = []
        self._flush(spec, batch, result)
        result["rows"] += len(seen)
        return seen

    def _flush(self, spec: TableSpec, batch: List[Dict[str, Any]], result: Dict[str, Any]) -> None:
        if not batch:
            return
        inserted, updated, _unchanged, changed = self.store.upsert_raw(spec.dt, batch)
        result["inserted"] += inserted
        result["updated"] += updated
        if changed:
            self.store.upsert_normalized(spec, changed)

    def _full_pull(self, spec: TableSpec, state: Dict[str, Any], result: Dict[str, Any], detect_deleted: bool) -> None:
        started_at = dt.datetime.now()
        rows = self.xt.client.iter_output(spec.dt, **self._read_params(spec))
        seen = self._ingest(spec, rows, result)
        if detect_deleted:
            missing = self.store.raw_ids(spec.dt) - seen
            if missing:
                self.store.mark_deleted(spec.dt, missing)
                self.store.mark_normalized_deleted(spec, missing)
                result["deleted"] = len(missing)
        self.store.set_state(
            spec.dt,
            lastid=max([self.store.max_raw_id(spec.dt), state.get("lastid") or 0]),
            lasttime=(started_at - LASTTIME_OVERLAP).strftime(TIME_FMT) if spec.mode == "lasttime" else state.get("lasttime"),
            last_full_at=started_at.replace(microsecond=0).isoformat(sep=" "),
        )

    def _lasttime_pull(self, spec: TableSpec, state: Dict[str, Any], result: Dict[str, Any]) -> None:
        started_at = dt.datetime.now()
        since = state.get("lasttime")
        params = self._read_params(spec)
        if since:
            params["lasttime"] = since
        self._ingest(spec, self.xt.client.iter_output(spec.dt, **params), result)
        self.store.set_state(spec.dt, lastid=self.store.max_raw_id(spec.dt), lasttime=(started_at - LASTTIME_OVERLAP).strftime(TIME_FMT))

    def _lastid_pull(self, spec: TableSpec, state: Dict[str, Any], result: Dict[str, Any]) -> None:
        lastid = int(state.get("lastid") or 0)
        rows = self.xt.client.iter_output(spec.dt, lastid=lastid, **self._read_params(spec))
        self._ingest(spec, rows, result)
        self.store.set_state(spec.dt, lastid=max(lastid, self.store.max_raw_id(spec.dt)))

    def _filtered_pull(self, spec: TableSpec, params: Dict[str, Any], result: Dict[str, Any]) -> None:
        merged = {**self._read_params(spec), **params}
        self._ingest(spec, self.xt.client.iter_output(spec.dt, **merged), result)

    # ------------------------------------------------------------------ 字典
    def refresh_dictionaries(self) -> Dict[str, Any]:
        summary: Dict[str, Any] = {"users": 0, "field_tables": 0, "dictionaries": 0, "failed": []}
        try:
            users = self.xt.client.users()
            self.store.save_dictionary("user", "pr2nm", [{"key": u.get("part"), "value": u.get("name"), "flag": "USE"} for u in users])
            summary["users"] = len(users)
        except Exception as exc:
            summary["failed"].append(f"users: {exc}")
        for dt_name in FIELD_NAME_TABLES:
            try:
                self.store.save_field_names(dt_name, self.xt.client.field_names(dt_name))
                summary["field_tables"] += 1
            except Exception as exc:
                summary["failed"].append(f"fields {dt_name}: {exc}")
        for dt_name, fields in DICT_FIELDS.items():
            for field_name in fields:
                try:
                    self.store.save_dictionary(dt_name, field_name, self.xt.client.dictionary(dt_name, field_name))
                    summary["dictionaries"] += 1
                except Exception as exc:
                    summary["failed"].append(f"dict {dt_name}.{field_name}: {exc}")
        logger.info("字典刷新：人员 %d，字段名表 %d，字典 %d，失败 %d", summary["users"], summary["field_tables"], summary["dictionaries"], len(summary["failed"]))
        return summary
