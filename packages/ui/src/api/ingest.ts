import { BASE, request, authHeaders, writeHeaders } from './client';

export interface IngestionLog {
  id: string;
  filename: string;
  status: "pending" | "processing" | "completed" | "failed" | "cancelling" | "cancelled";
  error_msg?: string;
  chunks_total?: number;
  chunks_done?: number;
  created_at: string;
  completed_at?: string;
  batch_id?: string;
  queue_position?: number;
  source_document_id?: string;
}

export const ingest = {
  upload: (wsId: string, file: File, docType: string = "generic", seeds?: string[], excelConfig?: Record<string, any>, meta?: { batch_id?: string; queue_position?: number }) => {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("doc_type", docType);
    if (seeds && seeds.length > 0) {
      formData.append("seeds", JSON.stringify(seeds));
    }
    if (excelConfig) {
      formData.append("excel_config", JSON.stringify(excelConfig));
    }
    if (meta?.batch_id) formData.append("batch_id", meta.batch_id);
    if (meta?.queue_position !== undefined) formData.append("queue_position", String(meta.queue_position));

    return fetch(`${BASE}/workspaces/${wsId}/ingest`, {
      method: "POST",
      headers: { ...authHeaders(), ...writeHeaders() },
      body: formData,
    }).then(async (res) => {
      if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
      return res.json();
    });
  },
  cancel: (wsId: string, jobId: string) => request("DELETE", `${BASE}/workspaces/${wsId}/ingest/${jobId}`),
  excelPreview: (wsId: string, file: File) => {
    const formData = new FormData();
    formData.append("file", file);
    return fetch(`${BASE}/workspaces/${wsId}/ingest/excel-preview`, {
      method: "POST",
      headers: { ...authHeaders(), ...writeHeaders() },
      body: formData,
    }).then(async (res) => {
      if (!res.ok) throw new Error((await res.json().catch(() => ({ detail: res.statusText }))).detail ?? res.statusText);
      return res.json();
    });
  },
  url: (wsId: string, url: string) => request("POST", `${BASE}/workspaces/${wsId}/ingest/url`, { url }),
  getLogs: (wsId: string) => request<IngestionLog[]>("GET", `${BASE}/workspaces/${wsId}/ingest/logs`),
  listSources: (wsId: string) => request<any[]>("GET", `${BASE}/workspaces/${wsId}/sources`),
  auditSource: (wsId: string, sourceId: string) => request<any>("GET", `${BASE}/workspaces/${wsId}/audit/${sourceId}`),
  retryAudit: (wsId: string, sourceId: string, missingHeadings: string[]) => 
    request<any>("POST", `${BASE}/workspaces/${wsId}/audit/${sourceId}/retry`, { headings: missingHeadings }),
};
