import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { GitFork, Brain, X } from 'lucide-react';
import { workspaces, ai, type Workspace, type WorkspaceCloneJob } from '../api';
import { useModal } from './ModalContext';

const KNOWN_EMBED_MODELS: Record<string, { id: string; dim: number }[]> = {
  openai: [
    { id: 'text-embedding-3-small', dim: 1536 },
    { id: 'text-embedding-3-large', dim: 3072 },
    { id: 'text-embedding-ada-002', dim: 1536 },
  ],
  gemini: [
    { id: 'text-embedding-004', dim: 768 },
  ],
  anthropic: [],  // no embedding API
};

export default function ForkWorkspaceModal({
  sourceWs,
  onForked,
  onClose,
}: {
  sourceWs: Workspace;
  onForked: (job: WorkspaceCloneJob, targetWs: Workspace) => void;
  onClose: () => void;
}) {
  const { i18n } = useTranslation();
  const zh = i18n.language === 'zh-TW';
  const { toast } = useModal();
  const [nameZh, setNameZh] = useState(`${sourceWs.name_zh} (Fork)`);
  const [nameEn, setNameEn] = useState(`${sourceWs.name_en} (Fork)`);
  const [embedModels, setEmbedModels] = useState<{ id: string; dim: number; provider: string }[]>([]);
  const [selectedEmbedModel, setSelectedEmbedModel] = useState<string>(sourceWs.embedding_model);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      ai.getCredits(),
      ai.getResolvedModel('embedding').catch(() => ({ provider: null, model: null }))
    ]).then(async ([credits, _]) => {
      const activeProviders = Object.entries(credits.has_own_key)
        .filter(([_, has]) => has)
        .map(([p]) => p);
      
      let allModels: { id: string; dim: number; provider: string }[] = [];
      
      for (const p of activeProviders) {
        if (p === 'anthropic') continue;
        try {
          const models = await ai.listModels(p);
          const embeds = models.filter(m => m.model_type === 'embedding');
          if (embeds.length > 0) {
            allModels.push(...embeds.map(m => ({ id: m.id, dim: m.embedding_dim ?? (KNOWN_EMBED_MODELS[p]?.find(k => k.id === m.id)?.dim ?? 768), provider: p })));
            continue;
          }
        } catch (e) {}
        const known = KNOWN_EMBED_MODELS[p] || [];
        allModels.push(...known.map(m => ({ ...m, provider: p })));
      }

      if (!allModels.find(m => m.id === sourceWs.embedding_model)) {
        allModels.unshift({ id: sourceWs.embedding_model, dim: sourceWs.embedding_dim, provider: 'inherited' });
      }
      setEmbedModels(allModels);
    }).catch(() => {
      setEmbedModels([{ id: sourceWs.embedding_model, dim: sourceWs.embedding_dim, provider: 'inherited' }]);
    });
  }, [sourceWs.embedding_model, sourceWs.embedding_dim]);

  const handleFork = async () => {
    if (!nameZh.trim() || !nameEn.trim()) {
      setError(zh ? '請填寫中英文名稱' : 'Both names are required');
      return;
    }
    setLoading(true);
    setError('');
    try {
      const job = await workspaces.fork(sourceWs.id, {
        name_zh: nameZh.trim(),
        name_en: nameEn.trim(),
        embedding_model: selectedEmbedModel || undefined,
      });
      const allWs = await workspaces.list();
      const targetWs = allWs.find(w => w.id === job.target_ws_id) ?? null;
      toast({ message: zh ? `🍴 Fork 已啟動，正在背景搬移節點…` : `🍴 Fork started — migrating nodes in background…`, variant: 'info' });
      if (targetWs) onForked(job, targetWs);
      else onClose();
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, zIndex: 200,
        background: 'var(--bg-overlay)', display: 'flex',
        alignItems: 'center', justifyContent: 'center',
      }}
      onMouseDown={e => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: 'var(--bg-surface)', border: '1px solid var(--border-default)',
        borderRadius: 16, padding: 32, width: 500, maxWidth: '90vw',
        boxShadow: 'var(--shadow-lg)',
      }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <GitFork size={20} color="var(--color-primary)" />
            <h2 style={{ fontSize: 18 }}>{zh ? 'Fork 知識庫' : 'Fork Knowledge Base'}</h2>
          </div>
          <button onClick={onClose} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}>
            <X size={18} />
          </button>
        </div>

        <div style={{ background: 'var(--bg-elevated)', padding: '8px 14px', borderRadius: 8, marginBottom: 20, border: '1px solid var(--border-subtle)', fontSize: 12, color: 'var(--text-muted)' }}>
          {zh ? '來源：' : 'Source: '}
          <span style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
            {zh ? sourceWs.name_zh : sourceWs.name_en}
          </span>
          {' '}
          <span style={{ opacity: 0.6 }}>· {sourceWs.embedding_model} ({sourceWs.embedding_dim}d)</span>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '新名稱（中文）' : 'New Name (Chinese)'}
            </label>
            <input className="mt-input" value={nameZh} onChange={e => setNameZh(e.target.value)} />
          </div>
          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
              {zh ? '新名稱（英文）' : 'New Name (English)'}
            </label>
            <input className="mt-input" value={nameEn} onChange={e => setNameEn(e.target.value)} />
          </div>

          <div>
            <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6 }}>
              <Brain size={12} />
              {zh ? '向量模型（建立後鎖定）' : 'Embedding Model (locked after creation)'}
            </label>
            {embedModels.length > 1 ? (
              <select
                className="mt-input"
                value={selectedEmbedModel}
                onChange={e => setSelectedEmbedModel(e.target.value)}
                style={{ width: '100%' }}
              >
                {embedModels.map(m => (
                  <option key={`${m.provider}-${m.id}`} value={m.id}>
                    {m.id} ({m.dim}d) — {m.provider.toUpperCase()}
                  </option>
                ))}
              </select>
            ) : (
              <div style={{ background: 'var(--bg-elevated)', padding: '8px 12px', borderRadius: 8, border: '1px solid var(--border-subtle)', fontSize: 12 }}>
                {selectedEmbedModel} ({sourceWs.embedding_dim}d)
              </div>
            )}
          </div>

          {error && <div style={{ color: 'var(--color-error)', fontSize: 13 }}>{error}</div>}

          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end', marginTop: 8 }}>
            <button className="btn-secondary" onClick={onClose} disabled={loading}>
              {zh ? '取消' : 'Cancel'}
            </button>
            <button className="btn-primary" onClick={handleFork} disabled={loading || !nameZh.trim() || !nameEn.trim()}>
              {loading ? (zh ? 'Fork 中…' : 'Forking…') : (zh ? '開始 Fork' : 'Start Fork')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
