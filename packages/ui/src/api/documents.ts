import { BASE, request, authHeaders, writeHeaders } from './client';

/**
 * Thrown by `documents.upload` when the workspace already contains a document
 * with identical content.  The UI should present the dedup dialog (S5-T21).
 */
export class DuplicateDocumentError extends Error {
  readonly existing: Document;
  constructor(existing: Document) {
    super(`Duplicate content: existing document "${existing.filename}"`);
    this.name = 'DuplicateDocumentError';
    this.existing = existing;
  }
}

export interface Document {
  id: string;
  workspace_id: string;
  filename: string;
  content_hash: string;
  mime_type: string;
  size_bytes: number;
  storage_path: string;
  title: string | null;
  summary: string | null;
  source_url: string | null;
  uploaded_by: string;
  uploaded_at: string;
  evidence_type: string;
  ingestion_job_id: string | null;
  linked_node_count: number;
}

export interface DocumentLinkedNode {
  id: string;
  title: string;
  content_type: string;
  status: string;
  paragraph_ref: string;
  excerpt: string | null;
}

export interface DocumentDetail extends Document {
  linked_nodes: DocumentLinkedNode[];
}

export interface NodeSource {
  id: string;
  filename: string;
  title: string | null;
  mime_type: string;
  size_bytes: number;
  uploaded_at: string;
  paragraph_ref: string;
  excerpt: string | null;
  source_url: string | null;
  evidence_type: string;
}

export const documents = {
  list: (wsId: string, limit = 20, offset = 0) =>
    request<Document[]>('GET', `${BASE}/workspaces/${wsId}/documents?limit=${limit}&offset=${offset}`),

  get: (wsId: string, docId: string) =>
    request<DocumentDetail>('GET', `${BASE}/workspaces/${wsId}/documents/${docId}`),

  preview: (wsId: string, docId: string) =>
    request<string>('GET', `${BASE}/workspaces/${wsId}/documents/${docId}/preview`),

  update: (wsId: string, docId: string, data: { title?: string; summary?: string; filename?: string }) =>
    request<Document>('PATCH', `${BASE}/workspaces/${wsId}/documents/${docId}`, data),

  delete: (wsId: string, docId: string) =>
    request('DELETE', `${BASE}/workspaces/${wsId}/documents/${docId}`),

  getNodeSources: (wsId: string, nodeId: string) =>
    request<NodeSource[]>('GET', `${BASE}/workspaces/${wsId}/nodes/${nodeId}/sources`),

  attachToNode: (wsId: string, nodeId: string, documentIds: string[], paragraphRef = '', excerpt?: string) =>
    request<{ created: number; node_id: string }>('POST', `${BASE}/workspaces/${wsId}/nodes/${nodeId}/document-links`, {
      document_ids: documentIds,
      paragraph_ref: paragraphRef,
      excerpt,
    }),

  detachFromNode: (wsId: string, nodeId: string, docId: string) =>
    request('DELETE', `${BASE}/workspaces/${wsId}/nodes/${nodeId}/document-links/${docId}`),

  contentUrl: (wsId: string, docId: string) =>
    `${BASE}/workspaces/${wsId}/documents/${docId}/content`,

  /**
   * Register an external URL as a document and optionally attach it to a node immediately.
   */
  linkUrl: (wsId: string, url: string, opts?: { title?: string; nodeId?: string }): Promise<Document> =>
    request<Document>('POST', `${BASE}/workspaces/${wsId}/documents/link-url`, {
      url,
      title: opts?.title,
      node_id: opts?.nodeId,
    }),

  /**
   * Upload a raw file as a document WITHOUT AI extraction (S5-T19).
   *
   * On duplicate content (409 DUPLICATE_CONTENT) throws `DuplicateDocumentError`
   * so the caller can display the dedup dialog (S5-T21).
   */
  upload: (wsId: string, file: File): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);
    return fetch(`${BASE}/workspaces/${wsId}/documents/upload`, {
      method: 'POST',
      headers: { ...authHeaders(), ...writeHeaders() },
      body: formData,
    }).then(async (res) => {
      if (res.status === 409) {
        const body = await res.json().catch(() => ({}));
        if (body.code === 'DUPLICATE_CONTENT' && body.existing_document) {
          throw new DuplicateDocumentError(body.existing_document as Document);
        }
      }
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail ?? `HTTP ${res.status}`);
      }
      return res.json();
    });
  },
};
