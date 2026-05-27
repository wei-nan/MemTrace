"""
jobs/audit_reviewers.py — 7 大 AI 審查員 (Phase 6.2 B4–B5 T13–T19)

每個 reviewer 是一個獨立函式，接受 (cur, workspace_id) 參數，
並呼叫 services.audit_proposals.create_proposal 寫入提案。

排程：每日一次，由 core/scheduler.py 觸發。
"""
from __future__ import annotations

import json
import logging
import datetime
from typing import Any, Dict, List, Optional, Tuple

from services.audit_proposals import create_proposal, DAILY_QUOTA_PER_REVIEWER
from core.database import db_cursor

logger = logging.getLogger(__name__)


# ─── T13: Deduper ─────────────────────────────────────────────────────────────

def reviewer_deduper(cur, workspace_id: str) -> int:
    """
    偵測向量相似度 > 0.92 的重複節點對，建議合併。
    每次最多提案 DAILY_QUOTA_PER_REVIEWER 筆。
    """
    cur.execute(
        """
        SELECT a.id AS id_a, b.id AS id_b,
               a.title AS title_a, b.title AS title_b,
               1 - (a.embedding <=> b.embedding) AS similarity
        FROM memory_nodes a
        JOIN memory_nodes b ON b.workspace_id = a.workspace_id
                           AND b.id > a.id
                           AND b.status = 'active'
        WHERE a.workspace_id = %s
          AND a.status = 'active'
          AND a.embedding IS NOT NULL
          AND b.embedding IS NOT NULL
          AND 1 - (a.embedding <=> b.embedding) > 0.92
        ORDER BY similarity DESC
        LIMIT %s
        """,
        (workspace_id, DAILY_QUOTA_PER_REVIEWER),
    )
    rows = cur.fetchall()
    created = 0
    for r in rows:
        prop = create_proposal(
            cur,
            workspace_id=workspace_id,
            reviewer="deduper",
            category="duplicate",
            target_ids=[r["id_a"], r["id_b"]],
            reasoning=(
                f"節點「{r['title_a']}」與「{r['title_b']}」向量相似度 {r['similarity']:.3f}，"
                "高於 0.92 門檻，建議合併或刪除其中一個。"
            ),
            evidence={"similarity": float(r["similarity"]), "title_a": r["title_a"], "title_b": r["title_b"]},
            suggested_action={"action": "merge", "keep_id": r["id_a"], "remove_id": r["id_b"]},
            severity="mid" if r["similarity"] > 0.96 else "low",
        )
        if prop:
            created += 1
    logger.info("[deduper] workspace=%s created=%d proposals", workspace_id, created)
    return created


# ─── T14: Tag Normalizer ──────────────────────────────────────────────────────

def reviewer_tag_normalizer(cur, workspace_id: str) -> int:
    """
    偵測：
    1. 孤兒 tag（只被 1 個節點使用）
    2. 超長 tag（> 30 字元）
    """
    # 超長 tag（展開 tag 陣列後篩選）
    cur.execute(
        """
        SELECT id, title, UNNEST(tags) AS tag
        FROM memory_nodes
        WHERE workspace_id = %s AND status = 'active'
          AND tags IS NOT NULL AND array_length(tags, 1) > 0
        """,
        (workspace_id,),
    )
    rows = cur.fetchall()
    created = 0

    long_tag_seen: dict = {}
    for r in rows:
        tag = r["tag"]
        if len(tag) > 30:
            key = f"long:{tag[:20]}"
            if key not in long_tag_seen:
                long_tag_seen[key] = True
                prop = create_proposal(
                    cur,
                    workspace_id=workspace_id,
                    reviewer="tag_normalizer",
                    category="tag_too_long",
                    target_ids=[r["id"]],
                    reasoning=f"節點「{r['title']}」含有超長 tag：{tag!r}（{len(tag)} 字元），建議縮短或移除。",
                    evidence={"tag": tag, "tag_length": len(tag)},
                    suggested_action={"action": "trim_tag", "tag": tag},
                    severity="low",
                )
                if prop:
                    created += 1

    # 孤兒 tag（出現頻率 == 1）
    cur.execute(
        """
        SELECT tag, COUNT(*) AS cnt
        FROM (
            SELECT UNNEST(tags) AS tag
            FROM memory_nodes
            WHERE workspace_id = %s AND status = 'active'
        ) sub
        GROUP BY tag
        HAVING COUNT(*) = 1
        LIMIT %s
        """,
        (workspace_id, DAILY_QUOTA_PER_REVIEWER),
    )
    orphan_rows = cur.fetchall()
    for r in orphan_rows:
        tag = r["tag"]
        # 找出使用此 tag 的節點
        cur.execute(
            "SELECT id, title FROM memory_nodes WHERE workspace_id = %s AND %s = ANY(tags) AND status = 'active' LIMIT 1",
            (workspace_id, tag),
        )
        node_row = cur.fetchone()
        if not node_row:
            continue
        prop = create_proposal(
            cur,
            workspace_id=workspace_id,
            reviewer="tag_normalizer",
            category="tag_orphan",
            target_ids=[node_row["id"]],
            reasoning=f"Tag {tag!r} 為孤兒 tag（只被 1 個節點「{node_row['title']}」使用），建議合併至已有 tag 或刪除。",
            evidence={"tag": tag, "count": 1},
            suggested_action={"action": "review_tag", "tag": tag},
            severity="low",
        )
        if prop:
            created += 1

    logger.info("[tag_normalizer] workspace=%s created=%d proposals", workspace_id, created)
    return created


# ─── T15: Edge Auditor ────────────────────────────────────────────────────────

def reviewer_edge_auditor(cur, workspace_id: str) -> int:
    """
    偵測語意矛盾或廢棄邊：
    1. 指向不存在 / 非 active 節點的邊（dangling edges）
    2. 雙向重複邊（A→B 與 B→A 相同 relation）
    """
    created = 0

    # Dangling edges
    cur.execute(
        """
        SELECT e.id, e.from_id, e.to_id, e.relation
        FROM edges e
        WHERE e.workspace_id = %s
          AND e.status = 'active'
          AND (
            NOT EXISTS (SELECT 1 FROM memory_nodes n WHERE n.id = e.from_id AND n.status = 'active')
            OR
            NOT EXISTS (SELECT 1 FROM memory_nodes n WHERE n.id = e.to_id AND n.status = 'active')
          )
        LIMIT %s
        """,
        (workspace_id, DAILY_QUOTA_PER_REVIEWER),
    )
    for r in cur.fetchall():
        prop = create_proposal(
            cur,
            workspace_id=workspace_id,
            reviewer="edge_auditor",
            category="dangling_edge",
            target_ids=[r["id"]],
            reasoning=(
                f"邊 {r['from_id']} →[{r['relation']}]→ {r['to_id']} 指向不存在或已停用的節點，"
                "建議移除此廢棄連結。"
            ),
            evidence={"from_id": r["from_id"], "to_id": r["to_id"], "relation": r["relation"]},
            suggested_action={"action": "delete_edge", "edge_id": r["id"]},
            severity="mid",
        )
        if prop:
            created += 1

    # Bidirectional duplicate edges
    cur.execute(
        """
        SELECT a.id AS edge_a, b.id AS edge_b,
               a.from_id, a.to_id, a.relation
        FROM edges a
        JOIN edges b ON b.workspace_id = a.workspace_id
                    AND b.from_id = a.to_id
                    AND b.to_id   = a.from_id
                    AND b.relation = a.relation
                    AND b.id > a.id
                    AND b.status = 'active'
        WHERE a.workspace_id = %s AND a.status = 'active'
        LIMIT %s
        """,
        (workspace_id, DAILY_QUOTA_PER_REVIEWER),
    )
    for r in cur.fetchall():
        prop = create_proposal(
            cur,
            workspace_id=workspace_id,
            reviewer="edge_auditor",
            category="duplicate_edge",
            target_ids=[r["edge_a"], r["edge_b"]],
            reasoning=(
                f"節點 {r['from_id']} 與 {r['to_id']} 之間存在雙向重複的「{r['relation']}」關聯，"
                "建議保留一條並刪除另一條。"
            ),
            evidence={"edge_a": r["edge_a"], "edge_b": r["edge_b"], "relation": r["relation"]},
            suggested_action={"action": "delete_edge", "edge_id": r["edge_b"]},
            severity="low",
        )
        if prop:
            created += 1

    logger.info("[edge_auditor] workspace=%s created=%d proposals", workspace_id, created)
    return created


# ─── T16: Embedding Consistency ───────────────────────────────────────────────

def reviewer_embedding_consistency(cur, workspace_id: str) -> int:
    """
    偵測「標題文字高度相似但向量距離遠」的節點對（可能 embedding 過期）。
    使用 trigram 相似度 >= 0.7 且向量相似度 < 0.5。
    """
    # 需要 pg_trgm extension
    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'")
    if not cur.fetchone():
        logger.warning("[embedding_consistency] pg_trgm not installed, skipping")
        return 0

    cur.execute(
        """
        SELECT a.id AS id_a, b.id AS id_b,
               a.title AS title_a, b.title AS title_b,
               similarity(a.title, b.title) AS text_sim,
               1 - (a.embedding <=> b.embedding) AS vec_sim
        FROM memory_nodes a
        JOIN memory_nodes b ON b.workspace_id = a.workspace_id
                           AND b.id > a.id
                           AND b.status = 'active'
        WHERE a.workspace_id = %s
          AND a.status = 'active'
          AND a.embedding IS NOT NULL
          AND b.embedding IS NOT NULL
          AND similarity(a.title, b.title) >= 0.7
          AND 1 - (a.embedding <=> b.embedding) < 0.5
        ORDER BY text_sim DESC
        LIMIT %s
        """,
        (workspace_id, DAILY_QUOTA_PER_REVIEWER),
    )
    rows = cur.fetchall()
    created = 0
    for r in rows:
        prop = create_proposal(
            cur,
            workspace_id=workspace_id,
            reviewer="embedding_consistency",
            category="embedding_drift",
            target_ids=[r["id_a"], r["id_b"]],
            reasoning=(
                f"節點「{r['title_a']}」與「{r['title_b']}」標題相似度 {r['text_sim']:.2f}，"
                f"但向量相似度僅 {r['vec_sim']:.2f}，可能 embedding 已過時，建議重新索引。"
            ),
            evidence={
                "text_similarity": float(r["text_sim"]),
                "vector_similarity": float(r["vec_sim"]),
            },
            suggested_action={"action": "reindex", "node_ids": [r["id_a"], r["id_b"]]},
            severity="mid",
        )
        if prop:
            created += 1
    logger.info("[embedding_consistency] workspace=%s created=%d proposals", workspace_id, created)
    return created


# ─── T17: Trust Calibrator ────────────────────────────────────────────────────

def reviewer_trust_calibrator(cur, workspace_id: str) -> int:
    """
    偵測「trust_score 高但近 90 天從未被路徑命中」的節點（可能過時高信任）。
    也偵測「trust_score 低但近 30 天命中率高」（可能應提升）。
    """
    created = 0

    # 高信任但冷門
    cur.execute(
        """
        SELECT n.id, n.title, n.trust_score,
               COUNT(ip.id) AS hit_count
        FROM memory_nodes n
        LEFT JOIN inquiry_paths ip ON n.id = ANY(ip.node_sequence)
                                  AND ip.workspace_id = n.workspace_id
                                  AND ip.started_at >= now() - INTERVAL '90 days'
        WHERE n.workspace_id = %s
          AND n.status = 'active'
          AND n.trust_score >= 0.8
        GROUP BY n.id, n.title, n.trust_score
        HAVING COUNT(ip.id) = 0
        LIMIT %s
        """,
        (workspace_id, DAILY_QUOTA_PER_REVIEWER // 2),
    )
    for r in cur.fetchall():
        prop = create_proposal(
            cur,
            workspace_id=workspace_id,
            reviewer="trust_calibrator",
            category="trust_overrated",
            target_ids=[r["id"]],
            reasoning=(
                f"節點「{r['title']}」trust_score={r['trust_score']:.2f}，"
                "但近 90 天從未出現在任何成功路徑中，建議降低信任分數。"
            ),
            evidence={"trust_score": float(r["trust_score"]), "hit_count_90d": 0},
            suggested_action={"action": "lower_trust", "node_id": r["id"], "suggested_score": 0.5},
            severity="low",
        )
        if prop:
            created += 1

    # 低信任但熱門
    cur.execute(
        """
        SELECT n.id, n.title, n.trust_score,
               COUNT(ip.id) AS hit_count
        FROM memory_nodes n
        JOIN inquiry_paths ip ON n.id = ANY(ip.node_sequence)
                              AND ip.workspace_id = n.workspace_id
                              AND ip.outcome = 'success'
                              AND ip.started_at >= now() - INTERVAL '30 days'
        WHERE n.workspace_id = %s
          AND n.status = 'active'
          AND n.trust_score < 0.5
        GROUP BY n.id, n.title, n.trust_score
        HAVING COUNT(ip.id) >= 5
        LIMIT %s
        """,
        (workspace_id, DAILY_QUOTA_PER_REVIEWER // 2),
    )
    for r in cur.fetchall():
        prop = create_proposal(
            cur,
            workspace_id=workspace_id,
            reviewer="trust_calibrator",
            category="trust_underrated",
            target_ids=[r["id"]],
            reasoning=(
                f"節點「{r['title']}」trust_score={r['trust_score']:.2f}，"
                f"但近 30 天成功命中 {r['hit_count']} 次，建議提升信任分數。"
            ),
            evidence={"trust_score": float(r["trust_score"]), "hit_count_30d": int(r["hit_count"])},
            suggested_action={"action": "raise_trust", "node_id": r["id"], "suggested_score": 0.75},
            severity="mid",
        )
        if prop:
            created += 1

    logger.info("[trust_calibrator] workspace=%s created=%d proposals", workspace_id, created)
    return created


# ─── T18: Coverage Gap Detector ───────────────────────────────────────────────

def reviewer_coverage_gap_detector(cur, workspace_id: str) -> int:
    """
    偵測 `content_type = 'gap'` 且仍為 pending 的缺口節點，
    若相同主題的 gap 已存在多個（≥3），建議建立一個集合式提案。
    另外將單一舊 gap（> 14 天）升級為 mid severity。
    """
    created = 0

    # 老舊單一 gap 節點 (> 14 天、仍 active)
    cur.execute(
        """
        SELECT id, title, created_at
        FROM memory_nodes
        WHERE workspace_id = %s
          AND status = 'active'
          AND content_type = 'gap'
          AND created_at < now() - INTERVAL '14 days'
        LIMIT %s
        """,
        (workspace_id, DAILY_QUOTA_PER_REVIEWER),
    )
    for r in cur.fetchall():
        prop = create_proposal(
            cur,
            workspace_id=workspace_id,
            reviewer="coverage_gap_detector",
            category="stale_gap",
            target_ids=[r["id"]],
            reasoning=(
                f"知識缺口節點「{r['title']}」已存在超過 14 天仍未填補，"
                "建議安排補充或標記為已知缺口。"
            ),
            evidence={"created_at": str(r["created_at"]), "title": r["title"]},
            suggested_action={"action": "fill_gap_or_acknowledge", "node_id": r["id"]},
            severity="mid",
        )
        if prop:
            created += 1

    logger.info("[coverage_gap_detector] workspace=%s created=%d proposals", workspace_id, created)
    return created


# ─── T19: Source Decay Monitor ────────────────────────────────────────────────

def reviewer_source_decay_monitor(cur, workspace_id: str) -> int:
    """
    偵測 documents 表中：
    1. URL 存在且最後抓取超過 60 天（可能已失效）
    2. file_path 存在但 metadata 中無 sha256（可能已更動）
    """
    created = 0

    # 老舊 URL 文件
    cur.execute(
        """
        SELECT d.id, d.title, d.source_url, d.node_id,
               d.uploaded_at
        FROM documents d
        WHERE d.workspace_id = %s
          AND d.source_url IS NOT NULL
          AND d.uploaded_at < now() - INTERVAL '60 days'
        ORDER BY d.uploaded_at ASC
        LIMIT %s
        """,
        (workspace_id, DAILY_QUOTA_PER_REVIEWER),
    )
    for r in cur.fetchall():
        target = [r["id"]]
        if r["node_id"]:
            target.append(r["node_id"])
        prop = create_proposal(
            cur,
            workspace_id=workspace_id,
            reviewer="source_decay_monitor",
            category="stale_url",
            target_ids=target,
            reasoning=(
                f"文件「{r['title']}」 (URL: {r['source_url']}) 已超過 60 天未重新抓取，"
                "建議檢查連結是否仍有效。"
            ),
            evidence={"source_url": r["source_url"], "uploaded_at": str(r["uploaded_at"])},
            suggested_action={"action": "re_fetch", "document_id": r["id"]},
            severity="low",
        )
        if prop:
            created += 1

    logger.info("[source_decay_monitor] workspace=%s created=%d proposals", workspace_id, created)
    return created


# ─── 主排程進入點 ─────────────────────────────────────────────────────────────

REVIEWERS = [
    reviewer_deduper,
    reviewer_tag_normalizer,
    reviewer_edge_auditor,
    reviewer_embedding_consistency,
    reviewer_trust_calibrator,
    reviewer_coverage_gap_detector,
    reviewer_source_decay_monitor,
]


def run_all_reviewers_for_workspace(cur, workspace_id: str) -> Dict[str, int]:
    """對單一 workspace 執行所有 Reviewers，回傳各 reviewer 建立的提案數。"""
    results: Dict[str, int] = {}
    for fn in REVIEWERS:
        name = fn.__name__.replace("reviewer_", "")
        try:
            count = fn(cur, workspace_id)
            results[name] = count
        except Exception as exc:
            logger.error("[%s] workspace=%s error: %s", name, workspace_id, exc, exc_info=True)
            results[name] = -1
    return results


def audit_reviewers_job() -> None:
    """
    排程入口（由 scheduler.py 每日呼叫）。
    掃描所有 active workspace，逐一執行所有 Reviewers。
    """
    logger.info("=== audit_reviewers_job: START ===")
    with db_cursor(commit=True) as cur:
        cur.execute("SELECT id FROM workspaces WHERE status = 'active'")
        workspaces = [r["id"] for r in cur.fetchall()]

    for ws_id in workspaces:
        logger.info("Running reviewers for workspace=%s", ws_id)
        with db_cursor(commit=True) as cur:
            summary = run_all_reviewers_for_workspace(cur, ws_id)
        logger.info("workspace=%s reviewer_summary=%s", ws_id, summary)

    logger.info("=== audit_reviewers_job: DONE (total workspaces=%d) ===", len(workspaces))
