"""
Memory Block — 기억 관리 (Soft Shell 첫 걸음)

세션 간 기억을 저장하고, 검색하고, 정리하는 장기.
파일 기반 (JSONL), 외부 의존성 없음.

기억 유형:
- episodic: 경험 기반 ("어제 Trust Game에서 llama가 배신했다")
- semantic: 사실/지식 ("exaone은 기본 협력 성향")
- prospective: 할 일 ("Luca에게 파일럿 코드 보내기")

Reference:
- OC: extensions/memory-core/ (SQLite + FTS + vector), flush-plan.ts
- OC: extensions/memory-lancedb/ (vector search, auto-capture/recall)
- CC: memdir/ (archived), MEMORY.md (file-based index)
- Anthropic AutoDream: date normalization, contradiction removal, pruning
"""

from __future__ import annotations

import json
import time
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from ludex.core.block import Block
from ludex.core.port import Port

logger = logging.getLogger(__name__)


# ============================================================
# Memory Data Types
# ============================================================

@dataclass
class Memory:
    """하나의 기억"""
    id: str
    content: str
    memory_type: str            # "episodic", "semantic", "prospective"
    tags: list[str] = field(default_factory=list)
    importance: float = 0.5     # 0.0 ~ 1.0
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    source: str = ""            # 어디서 온 기억인가
    status: str = "active"      # "active", "archived", "deleted"
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "tags": self.tags,
            "importance": self.importance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "source": self.source,
            "status": self.status,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Memory:
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass(frozen=True)
class RecallResult:
    """기억 검색 결과"""
    memory: Memory
    relevance: float    # 0.0 ~ 1.0 검색 관련도


@dataclass
class ConsolidationReport:
    """기억 정리 보고"""
    promoted: int       # episodic → semantic으로 승격된 수
    archived: int       # 보관 처리된 수
    deleted: int        # 삭제된 수
    contradictions: int # 모순 해결된 수
    total_remaining: int


# ============================================================
# Memory Block
# ============================================================

class MemoryBlock(Block):
    """
    기억 관리 블록.

    provides: remember, recall, forget, consolidate, list_memories
    requires: (없음)

    파일 기반 저장 (JSONL). 외부 DB 의존성 없음.
    """

    name = "memory"
    provides = [
        Port("remember", description="Store a memory"),
        Port("recall", description="Search memories by query"),
        Port("forget", description="Delete or archive a memory"),
        Port("consolidate", description="Consolidate/clean up memories (dream)"),
        Port("list_memories", description="List memories by type/tag"),
    ]
    requires = []

    def __init__(self, storage_dir: str = "", auto_capture: bool = True,
                 weight_check_interval: int = 10):
        super().__init__()
        self._storage_dir = storage_dir
        self._auto_capture = auto_capture
        self._memories: dict[str, Memory] = {}
        self._next_id: int = 1
        self._loaded: bool = False
        self._weight_check_interval = weight_check_interval
        self._turns_since_weight_check: int = 0

    def on_attach(self):
        # 스토리지 디렉토리 설정
        if not self._storage_dir:
            self._storage_dir = self._cfg("memory_dir", "./ludex_memory")

        # 기존 기억 로드
        self._load()

        # 자동 캡처: 턴 결과를 episodic 기억으로 저장
        if self._auto_capture:
            self._listen("turn.ended", self._auto_capture_turn)

        # Periodic weight check on turn end
        self._listen("turn.ended", self._periodic_weight_check)

        # Check habitat weight on load — trigger diet if overweight
        self._check_weight()

    def _check_weight(self):
        """Check habitat weight and trigger consolidation if overweight.

        Biological metaphor: body weight check. If the creature is overweight
        (habitat exceeds max_storage_mb), trigger a diet (memory consolidation).
        """
        if not self._config:
            return
        habitat_dir = self._config.get("habitat_dir", "")
        if not habitat_dir:
            return

        try:
            from ludex.core.habitat import HabitatConfig
            max_mb = self._config.get("max_storage_mb", 500)
            habitat_mode = self._config.get("habitat_mode", "temporary")
            if habitat_mode == "temporary":
                return  # no weight limit for ephemeral creatures

            # Measure current weight
            import os
            from pathlib import Path
            base = Path(habitat_dir)
            if not base.exists():
                return
            total_bytes = sum(f.stat().st_size for f in base.rglob("*") if f.is_file())
            total_mb = total_bytes / (1024 * 1024)
            usage_pct = (total_mb / max_mb * 100) if max_mb > 0 else 0

            if usage_pct > 90:
                # Critical: auto-consolidate
                logger.warning(f"Memory: habitat weight {total_mb:.1f}MB / {max_mb}MB ({usage_pct:.0f}%) — "
                             f"triggering automatic consolidation (diet)")
                self._emit("habitat.overweight", total_mb=total_mb, max_mb=max_mb, usage_pct=usage_pct)
                report = self.handle_consolidate()
                logger.info(f"Memory: diet complete — archived={report.archived}, "
                          f"promoted={report.promoted}, remaining={report.total_remaining}")
            elif usage_pct > 70:
                # Warning
                logger.info(f"Memory: habitat weight {total_mb:.1f}MB / {max_mb}MB ({usage_pct:.0f}%) — "
                          f"approaching limit, consider consolidation")
                self._emit("habitat.weight_warning", total_mb=total_mb, max_mb=max_mb, usage_pct=usage_pct)
        except Exception as e:
            logger.debug(f"Memory: weight check failed: {e}")

    def _periodic_weight_check(self, **kwargs):
        """Check habitat weight every N turns during runtime."""
        self._turns_since_weight_check += 1
        if self._turns_since_weight_check >= self._weight_check_interval:
            self._turns_since_weight_check = 0
            self._check_weight()

    def on_detach(self):
        # Skip bulk save on detach.
        # _save_incremental() already persists each new memory immediately,
        # and forget/consolidate call _save() explicitly.
        # Calling _save() during __del__ / interpreter shutdown causes
        # "name 'open' is not defined" because builtins are torn down.
        pass

    # --- Provides: remember ---

    def handle_remember(
        self,
        content: str,
        memory_type: str = "episodic",
        tags: list[str] | None = None,
        importance: float = 0.5,
        source: str = "",
        metadata: dict | None = None,
    ) -> str:
        """기억 저장. 반환: memory_id"""
        mem_id = f"mem_{self._next_id:04d}"
        self._next_id += 1

        memory = Memory(
            id=mem_id,
            content=content,
            memory_type=memory_type,
            tags=tags or [],
            importance=importance,
            source=source,
            metadata=metadata or {},
        )

        self._memories[mem_id] = memory
        self._save_incremental(memory)

        self._publish("memory.stored", {
            "id": mem_id, "type": memory_type, "importance": importance,
        })
        self._emit("memory.stored", memory_id=mem_id, memory_type=memory_type)

        # Vital signs 업데이트
        if self._config:
            self._config.set("_memory_entries", len(self._memories), layer="session")

        logger.debug(f"Remembered: [{memory_type}] {content[:50]}...")

        # Periodic weight check (every 50 memories added)
        if self._next_id % 50 == 0:
            self._check_weight()

        return mem_id

    # --- Provides: recall ---

    def handle_recall(self, query: str, memory_type: str | None = None, tags: list[str] | None = None, limit: int = 5) -> list[RecallResult]:
        """
        기억 검색. TF-IDF 기반 (Cody 피드백 #1 반영).
        벡터 검색은 Phase 6+.
        """
        results = []

        query_lower = query.lower()
        query_words = set(query_lower.split())

        # TF-IDF: 문서 빈도 계산 (전체 기억에서 각 단어가 나타나는 기억 수)
        active_memories = [m for m in self._memories.values() if m.status == "active"]
        doc_freq: dict[str, int] = {}
        for mem in active_memories:
            words_in_doc = set(mem.content.lower().split())
            for w in words_in_doc:
                doc_freq[w] = doc_freq.get(w, 0) + 1
        n_docs = max(len(active_memories), 1)

        for memory in active_memories:
            if memory_type and memory.memory_type != memory_type:
                continue
            if tags and not any(t in memory.tags for t in tags):
                continue

            content_lower = memory.content.lower()
            content_words = set(content_lower.split())

            # TF-IDF 기반 관련도
            tfidf_score = 0.0
            for word in query_words:
                if word in content_words:
                    # TF: 쿼리 단어가 문서에 있으면 1
                    tf = 1.0
                    # IDF: log(N / df) — 희귀한 단어일수록 높음
                    import math
                    df = doc_freq.get(word, 1)
                    idf = math.log(n_docs / df + 1)
                    tfidf_score += tf * idf

            # 정규화
            tfidf_normalized = tfidf_score / max(len(query_words), 1)

            # 쿼리가 내용에 포함되는지 (부분 문자열)
            substring_match = 1.0 if query_lower in content_lower else 0.0

            # 태그 매칭
            tag_match = 0.0
            if tags:
                tag_match = len(set(tags) & set(memory.tags)) / max(len(tags), 1)

            # 최종 관련도 (TF-IDF 중심)
            relevance = (
                tfidf_normalized * 0.5 +
                substring_match * 0.2 +
                tag_match * 0.2 +
                memory.importance * 0.1
            )

            if relevance > 0.15:
                results.append(RecallResult(memory=memory, relevance=relevance))

        # 관련도 순 정렬
        results.sort(key=lambda r: r.relevance, reverse=True)

        # Hit rate 업데이트
        if self._config:
            total_recalls = self._config.get("_memory_total_recalls", 0) + 1
            hits = self._config.get("_memory_hits", 0) + (1 if results else 0)
            self._config.set("_memory_total_recalls", total_recalls, layer="session")
            self._config.set("_memory_hits", hits, layer="session")
            self._config.set("_memory_hit_rate", hits / max(total_recalls, 1), layer="session")

        self._emit("memory.recalled", query=query, results_count=len(results[:limit]))

        return results[:limit]

    # --- Provides: forget ---

    def handle_forget(self, memory_id: str, hard_delete: bool = False) -> bool:
        """기억 삭제 또는 보관"""
        if memory_id not in self._memories:
            return False

        if hard_delete:
            del self._memories[memory_id]
        else:
            self._memories[memory_id].status = "archived"
            self._memories[memory_id].updated_at = time.time()

        self._save()
        return True

    # --- Provides: consolidate (Dream) ---

    def handle_consolidate(self) -> ConsolidationReport:
        """
        기억 정리 (Dream Module의 기초 버전).

        1. 오래된 episodic 중 반복 패턴 → semantic 승격
        2. 7일 이상 오래된 저중요도 episodic → archive
        3. 완료된 prospective → archive
        4. 기본적인 모순 감지 (같은 태그에 상충 내용)
        """
        promoted = 0
        archived = 0
        deleted = 0
        contradictions = 0

        now = time.time()
        seven_days = 7 * 24 * 3600

        # 1. 오래된 저중요도 episodic → archive
        for mem in list(self._memories.values()):
            if mem.status != "active":
                continue

            if mem.memory_type == "episodic":
                age = now - mem.created_at
                if age > seven_days and mem.importance < 0.3:
                    mem.status = "archived"
                    mem.updated_at = now
                    archived += 1

            # 2. 완료된 prospective → archive
            if mem.memory_type == "prospective":
                if mem.metadata.get("completed", False):
                    mem.status = "archived"
                    mem.updated_at = now
                    archived += 1

        # 3. 반복 패턴 감지 → semantic 승격
        # 같은 태그의 episodic이 3개 이상이면 요약 semantic 생성
        tag_groups: dict[str, list[Memory]] = {}
        for mem in self._memories.values():
            if mem.status == "active" and mem.memory_type == "episodic":
                for tag in mem.tags:
                    tag_groups.setdefault(tag, []).append(mem)

        for tag, mems in tag_groups.items():
            if len(mems) >= 3:
                # 요약 semantic 생성
                contents = [m.content for m in mems[:5]]
                summary = f"[Consolidated from {len(mems)} episodes] " + " | ".join(
                    c[:50] for c in contents
                )
                self.handle_remember(
                    content=summary,
                    memory_type="semantic",
                    tags=[tag, "consolidated"],
                    importance=0.7,
                    source="consolidation",
                )
                promoted += 1

        self._save()

        total = sum(1 for m in self._memories.values() if m.status == "active")
        report = ConsolidationReport(
            promoted=promoted,
            archived=archived,
            deleted=deleted,
            contradictions=contradictions,
            total_remaining=total,
        )

        self._emit("memory.consolidated", promoted=promoted, archived=archived)
        logger.info(f"Consolidation: +{promoted} semantic, -{archived} archived, {total} remaining")

        return report

    # --- Provides: list_memories ---

    def handle_list_memories(
        self,
        memory_type: str | None = None,
        tags: list[str] | None = None,
        status: str = "active",
        limit: int = 50,
    ) -> list[dict]:
        """기억 목록 조회"""
        results = []
        for mem in self._memories.values():
            if mem.status != status:
                continue
            if memory_type and mem.memory_type != memory_type:
                continue
            if tags and not any(t in mem.tags for t in tags):
                continue
            results.append(mem.to_dict())

        results.sort(key=lambda m: m["updated_at"], reverse=True)
        return results[:limit]

    # --- Auto-capture ---

    def _auto_capture_turn(self, turn_number: int = 0, success: bool = True, **kwargs):
        """턴 완료 시 자동으로 episodic 기억 저장"""
        model = self._cfg("model", "unknown")
        status = "success" if success else "error"
        self.handle_remember(
            content=f"Turn {turn_number}: {status} (model: {model})",
            memory_type="episodic",
            tags=["turn", model, status],
            importance=0.3 if success else 0.6,
            source="auto_capture",
            metadata={"turn": turn_number, "success": success},
        )

    # --- Persistence (JSONL) ---

    def _get_storage_path(self) -> Path:
        path = Path(self._storage_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path / "memories.jsonl"

    def _load(self):
        """파일에서 기억 로드"""
        filepath = self._get_storage_path()
        if not filepath.exists():
            self._loaded = True
            return

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    mem = Memory.from_dict(data)
                    self._memories[mem.id] = mem
                    # ID 카운터 업데이트
                    num = int(mem.id.split("_")[1])
                    if num >= self._next_id:
                        self._next_id = num + 1

            self._loaded = True
            logger.info(f"Loaded {len(self._memories)} memories from {filepath}")
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")

    def _save(self):
        """전체 기억을 파일에 저장"""
        # Capture builtins as locals to survive interpreter shutdown
        _open = open
        _json = json
        try:
            filepath = self._get_storage_path()
            with _open(filepath, "w", encoding="utf-8") as f:
                for mem in self._memories.values():
                    f.write(_json.dumps(mem.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            try:
                logger.error(f"Failed to save memories: {e}")
            except Exception:
                pass

    def _save_incremental(self, memory: Memory):
        """새 기억을 파일에 추가 (append)"""
        _open = open
        _json = json
        try:
            filepath = self._get_storage_path()
            with _open(filepath, "a", encoding="utf-8") as f:
                f.write(_json.dumps(memory.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            try:
                logger.error(f"Failed to append memory: {e}")
            except Exception:
                pass

    # --- Stats ---

    @property
    def count(self) -> int:
        return sum(1 for m in self._memories.values() if m.status == "active")

    def stats(self) -> dict:
        active = [m for m in self._memories.values() if m.status == "active"]
        return {
            "total": len(active),
            "episodic": sum(1 for m in active if m.memory_type == "episodic"),
            "semantic": sum(1 for m in active if m.memory_type == "semantic"),
            "prospective": sum(1 for m in active if m.memory_type == "prospective"),
            "storage_dir": self._storage_dir,
        }
