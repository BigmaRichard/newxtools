"""本地维护的小数据（不进镜像库、不进仓库）：目前只有“严重逾期”标记的手工解除名单。

文件 data/severe_exempt.json：[{"id": 客户 id, "name": 客户名, "note": 备注, "since": "YYYY-MM-DD"}]。
前台按文件修改时间热加载，改完立即生效，不用重启服务。
"""
from __future__ import annotations

import datetime as dt
import json
import os
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


class SevereExempt:
    """严重逾期标记的手工解除名单（按客户 id）。"""

    def __init__(self, path: Path):
        self.path = Path(path)
        self._lock = threading.Lock()
        self._entries: Dict[int, Dict[str, Any]] = {}
        self._mtime: Optional[Tuple[int, int]] = None
        self._checked = 0.0

    # ---- 读
    def _load(self) -> None:
        try:
            st = os.stat(self.path)
            mtime = (st.st_mtime_ns, st.st_size)   # 同一秒内连续改写时 mtime 可能不变，连大小一起比
        except FileNotFoundError:
            self._entries, self._mtime = {}, None
            return
        if mtime == self._mtime:
            return
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8") or "[]")
        except (OSError, ValueError):
            raw = []
        entries: Dict[int, Dict[str, Any]] = {}
        for e in raw if isinstance(raw, list) else []:
            try:
                cid = int(e.get("id"))
            except (TypeError, ValueError, AttributeError):
                continue
            entries[cid] = {"id": cid, "name": str(e.get("name") or ""), "note": str(e.get("note") or ""), "since": str(e.get("since") or "")}
        self._entries, self._mtime = entries, mtime

    def refresh(self, force: bool = False) -> None:
        with self._lock:
            now = time.time()
            if force or now - self._checked > 2:   # 最多每 2 秒 stat 一次文件
                self._checked = now
                self._load()

    def get(self, cid: Any) -> Optional[Dict[str, Any]]:
        try:
            cid = int(cid)
        except (TypeError, ValueError):
            return None
        self.refresh()
        return self._entries.get(cid)

    def all(self) -> List[Dict[str, Any]]:
        self.refresh(force=True)
        return sorted(self._entries.values(), key=lambda e: e["since"], reverse=True)

    # ---- 写
    def _save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(list(self._entries.values()), ensure_ascii=False, indent=2), encoding="utf-8")
        os.replace(tmp, self.path)
        st = os.stat(self.path)
        self._mtime = (st.st_mtime_ns, st.st_size)

    def add(self, cid: int, name: str, note: str = "") -> Dict[str, Any]:
        with self._lock:
            self._load()
            entry = {"id": int(cid), "name": name or "", "note": note or "", "since": dt.date.today().isoformat()}
            self._entries[int(cid)] = entry
            self._save()
            return entry

    def remove(self, cid: int) -> bool:
        with self._lock:
            self._load()
            gone = self._entries.pop(int(cid), None) is not None
            if gone:
                self._save()
            return gone
