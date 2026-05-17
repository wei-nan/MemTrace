import asyncio
import json
import logging
from typing import List, Tuple, Optional
from core.ai import (
    chat_completion, extract_nodes_structured,
    record_usage, resolve_provider, strip_fences, AIProviderUnavailable
)
from core.database import db_cursor
from core.security import generate_id
from core.adapters import NormalizedDocument
from services.ingest.parser import chunk_text, scan_api_endpoints
from services.ingest.persistence import persist_nodes, persist_nodes_sync, detect_cross_file_associations_for_nodes

logger = logging.getLogger(__name__)

# Limit concurrent AI extraction calls
AI_SEMAPHORE = asyncio.Semaphore(3)

def resolve_with_fallback(user_id: str, feature: str):
    """
    Try each provider the user has configured, in order of last_used_at.
    Returns the first ResolvedProvider that can be instantiated.
    """
    with db_cursor() as cur:
        cur.execute(
            """SELECT provider FROM user_ai_keys 
               WHERE user_id = %s 
               ORDER BY last_used_at DESC NULLS LAST""",
            (user_id,),
        )
        providers = [row["provider"] for row in cur.fetchall()]

    last_exc: Exception = AIProviderUnavailable("No AI provider keys configured.")
    for provider_name in providers:
        try:
            return resolve_provider(user_id, feature, preferred_provider=provider_name)
        except AIProviderUnavailable as e:
            last_exc = e
            continue
    raise last_exc

async def safe_parse_nodes_with_repair(raw: str, resolved, filename: str) -> Tuple[List[dict], int]:
    """Parse the LLM response as a JSON node array with repair logic."""
    from services.ingest.normalize import normalize_nodes, extract_objects_partial
    
    cleaned = strip_fences(raw)
    if not cleaned.strip():
        return [], 0

    # Pass 1: direct parse
    try:
        result = json.loads(cleaned)
        if isinstance(result, list):
            return normalize_nodes(result, filename), 0
        if isinstance(result, dict):
            return normalize_nodes([result], filename), 0
    except json.JSONDecodeError:
        pass

    # Pass 2: partial object extraction
    partial = extract_objects_partial(cleaned)
    if partial:
        return normalize_nodes(partial, filename), 0

    # Pass 3: LLM repair
    try:
        repair_messages = [
            {"role": "system", "content": "You are a JSON repair assistant. Return ONLY a valid JSON array of node objects."},
            {"role": "user", "content": f"Repair this broken JSON from '{filename}':\n\n{cleaned[:6000]}"},
        ]
        repaired_raw, repair_tokens = await chat_completion(resolved, repair_messages, max_tokens=4096)
        repaired_cleaned = strip_fences(repaired_raw)
        result = json.loads(repaired_cleaned)
        if isinstance(result, list):
            return normalize_nodes(result, filename), repair_tokens
        if isinstance(result, dict):
            return normalize_nodes([result], filename), repair_tokens
    except Exception as e:
        logger.error(f"JSON repair failed for {filename}: {e}")

    return [], 0

async def process_ingestion(job_id: str, ws_id: str, content: str, user_id: str, filename: str, 
                            doc_type: str = "generic", approved_seeds: Optional[List[str]] = None, 
                            doc: Optional[NormalizedDocument] = None):
    """Main ingestion pipeline orchestration."""
    await AI_SEMAPHORE.acquire()
    try:
        with db_cursor(commit=True) as cur:
            cur.execute(
                """UPDATE ingestion_logs 
                   SET status = 'processing', started_at = now() 
                   WHERE id = %s AND status = 'pending'""",
                (job_id,),
            )
            if cur.rowcount == 0:
                return # cancelled or already running

        source_id = generate_id("src")
        src_node_id = generate_id("mem")
        
        # 1. Normalize content for storage
        if doc:
            content = "\n\n".join([f"{' '.join(s.heading_chain + ([s.heading] if s.heading else []))}\n{s.content}" for s in doc.segments])
        
        # 2. Record source
        with db_cursor(commit=True) as cur:
            page_count = doc.metadata.get("page_count") if doc else None
            has_ocr    = doc.metadata.get("has_ocr")    if doc else False
            cur.execute(
                """INSERT INTO import_sources (id, workspace_id, filename, doc_type, raw_content, page_count, has_ocr)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (source_id, ws_id, filename, doc_type, content, page_count, has_ocr)
            )

        # 3. Resolve AI provider
        with db_cursor() as cur:
            cur.execute("""SELECT extraction_provider FROM workspaces WHERE id = %s""", (ws_id,))
            ws_row = cur.fetchone()
        ws_extraction_provider = ws_row["extraction_provider"] if ws_row else None

        if ws_extraction_provider:
            resolved = resolve_provider(user_id, "extraction", preferred_provider=ws_extraction_provider)
        else:
            resolved = resolve_with_fallback(user_id, "extraction")

        # Build cluster context string for the AI prompt
        from services.clusters import fetch_clusters_for_prompt
        cluster_list = fetch_clusters_for_prompt(ws_id)
        cluster_context: str = ""
        if cluster_list:
            names = ", ".join(f'{c["name_en"]} ({c["name_zh"]})' for c in cluster_list)
            cluster_context = (
                f"Existing clusters in this workspace: [{names}]. "
                "Assign each node to the best-matching cluster using its exact name, "
                "or propose a new short cluster name only when no existing cluster fits."
            )

        total_tokens = 0

        # 4. API Seed nodes
        seed_nodes = scan_api_endpoints(content)
        if approved_seeds is not None:
            seed_nodes = [n for n in seed_nodes if n["title_en"] in approved_seeds]

        if seed_nodes:
            with db_cursor(commit=True) as cur:
                persist_nodes_sync(cur, ws_id, seed_nodes, job_id, filename, user_id, resolved, source_id=source_id, is_seed=True, source_doc_node_id=src_node_id)

        # 5. Source document node
        with db_cursor(commit=True) as cur:
            cur.execute(
                """INSERT INTO memory_nodes
                    (id, workspace_id, title_zh, title_en, content_type, content_format,
                     body_zh, body_en, tags, visibility, author, signature, source_type, source_file, status)
                VALUES
                    (%s, %s, %s, %s, 'source_document', 'plain',
                     %s, '', ARRAY[]::text[], 'private', %s, 'source', 'human', %s, 'active')
                ON CONFLICT (id) DO NOTHING""",
                (src_node_id, ws_id, f"來源文件：{filename}", f"Source: {filename}", content[:50000], user_id, filename)
            )

        # 6. Extraction loop
        all_review_ids = []
        chunks = []
        if doc:
            for s in doc.segments:
                chunks.append((s.content, s.heading_chain + ([s.heading] if s.heading else [])))
        else:
            chunks = chunk_text(content)

        for i, (chunk_text_data, headings) in enumerate(chunks):
            try:
                # Update progress
                with db_cursor(commit=True) as cur:
                    progress = int(((i + 1) / len(chunks)) * 100)
                    cur.execute("""UPDATE ingestion_logs SET progress = %s WHERE id = %s""", (progress, job_id))

                # Extract
                raw_nodes, tokens = await extract_nodes_structured(
                    resolved, chunk_text_data, headings,
                    doc_type=doc_type, cluster_context=cluster_context or None,
                )
                total_tokens += tokens
                record_usage(resolved, "extraction", tokens, workspace_id=ws_id)

                # Parse & Normalize
                nodes_data, repair_tokens = await safe_parse_nodes_with_repair(raw_nodes, resolved, filename)
                total_tokens += repair_tokens
                if repair_tokens:
                    record_usage(resolved, "extraction", repair_tokens, workspace_id=ws_id)

                for n in nodes_data:
                    n["source_segment"] = chunk_text_data[:2000]

                # Resolve cluster_id from AI-proposed names
                if nodes_data:
                    from services.clusters import get_or_create_cluster
                    with db_cursor(commit=True) as cl_cur:
                        for n in nodes_data:
                            cname_zh = n.pop("cluster_name_zh", None) or ""
                            cname_en = n.pop("cluster_name_en", None) or ""
                            if cname_en:
                                try:
                                    n["cluster_id"] = get_or_create_cluster(
                                        cl_cur, ws_id, cname_zh or cname_en, cname_en
                                    )
                                except Exception:
                                    pass

                # Persist
                para_ref = f"Chunk {i+1}"
                if headings:
                    para_ref += f" ({' > '.join(headings)})"
                
                with db_cursor(commit=True) as cur:
                    r_ids = await persist_nodes(
                        cur, ws_id, nodes_data, job_id, filename, user_id, resolved, 
                        source_id=source_id, doc_type=doc_type, 
                        source_doc_node_id=src_node_id, source_paragraph_ref=para_ref
                    )
                    all_review_ids.extend([rid for rid, _ in r_ids if rid])

            except Exception as chunk_err:
                logger.error(f"Error processing chunk {i} of {filename}: {chunk_err}")

        # 7. Cross-file associations
        detect_cross_file_associations_for_nodes(ws_id, all_review_ids, is_proposal=True)

        # P4.8-S9-7-1: Trigger background enrichment for new review items
        from services.bg_jobs import bg_suggest_edges, bg_check_complexity
        from core.scheduler import scheduler
        for rid in all_review_ids:
            if rid:
                # We use scheduler or background_tasks if available. 
                # Since we are in a background thread already, we can just call them or use scheduler.
                # Here we'll use a simple background_tasks if we had access to it, 
                # but process_ingestion doesn't have it. We'll use scheduler.
                scheduler.add_job(bg_suggest_edges, args=[ws_id, rid, user_id])
                # Complexity check usually needs the node to be in memory_nodes, 
                # but for S9-3 we might want to check the proposal.
                # For now, we'll follow the requirement to trigger it.
                scheduler.add_job(bg_check_complexity, args=[ws_id, rid, user_id])

        # 8. Finalize
        with db_cursor(commit=True) as cur:
            cur.execute(
                """UPDATE ingestion_logs 
                   SET status = 'completed', completed_at = now(), progress = 100,
                       estimated_tokens = %s
                   WHERE id = %s""",
                (total_tokens, job_id),
            )

    except Exception as e:
        logger.exception(f"Ingestion failed for {filename}: {e}")
        with db_cursor(commit=True) as cur:
            cur.execute("""UPDATE ingestion_logs SET status = 'failed', error_message = %s WHERE id = %s""", (str(e), job_id))
    finally:
        AI_SEMAPHORE.release()
