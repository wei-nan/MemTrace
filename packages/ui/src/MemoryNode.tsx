import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Handle, Position } from 'reactflow';
import { AlertTriangle } from 'lucide-react';

const TYPE_COLORS: Record<string, string> = {
  factual:    '#6366f1',
  procedural: '#22c55e',
  preference: '#f59e0b',
  context:    '#64748b',
};
const DEFAULT_COLOR = '#6366f1';

const MemoryNode = ({ data }: { data: any }) => {
  const { t } = useTranslation();
  const lod: string = data.lod ?? 'full';

  // ── dot LOD ──────────────────────────────────────────────────────────────
  if (lod === 'dot') {
    return (
      <>
        <Handle type="target" position={Position.Top} style={{ opacity: 0, pointerEvents: 'none' }} />
        <div
          title={data.title}
          style={{
            width: 12,
            height: 12,
            borderRadius: '50%',
            background: data.healthColor || TYPE_COLORS[data.type] || DEFAULT_COLOR,
            opacity: 0.85,
            boxShadow: `0 0 4px ${data.healthColor || TYPE_COLORS[data.type] || DEFAULT_COLOR}88`,
            transition: 'all 0.2s ease',
          }}
        />
        <Handle type="source" position={Position.Bottom} style={{ opacity: 0, pointerEvents: 'none' }} />
      </>
    );
  }

  // ── compact LOD ───────────────────────────────────────────────────────────
  if (lod === 'compact') {
    return (
      <div
        className="glass-panel"
        title={data.title}
        style={{
          padding: '5px 10px',
          minWidth: 120,
          maxWidth: 160,
          border: `1px solid ${data.healthColor || 'var(--border-strong)'}`,
          background: 'var(--bg-surface)',
          transition: 'all 0.2s ease',
        }}
      >
        <Handle type="target" position={Position.Top} style={{ background: 'var(--color-primary)' }} />
        <div style={{
          fontSize: '0.75rem',
          fontWeight: 600,
          color: 'var(--text-primary)',
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          maxWidth: 140,
        }}>
          {(data.title || '').slice(0, 20)}
        </div>
        <Handle type="source" position={Position.Bottom} style={{ background: 'var(--color-primary)' }} />
      </div>
    );
  }

  // ── full & expanded LOD ───────────────────────────────────────────────────
  const isExpired = data.validityExpired;
  const isExpanded = lod === 'expanded';
  const bodyPreview = (data.bodyPreview || '').slice(0, 80);

  return (
    <div
      className="glass-panel"
      title={data.healthTooltip || undefined}
      style={{
        padding: '12px 16px',
        minWidth: isExpanded ? '220px' : '200px',
        border: `1px solid ${data.healthColor || 'var(--border-strong)'}`,
        boxShadow: data.healthColor ? `0 0 0 1px ${data.healthColor}40, var(--shadow-md)` : 'var(--shadow-md)',
        background: data.healthColor ? `color-mix(in srgb, ${data.healthColor} 8%, var(--bg-surface))` : undefined,
        position: 'relative',
        transition: 'all 0.2s ease',
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: 'var(--color-primary)' }} />

      {isExpired && (
        <div style={{ position: 'absolute', top: -10, left: -10, color: '#eab308', background: 'var(--bg-surface)', borderRadius: '50%', padding: 2, boxShadow: 'var(--shadow-sm)', zIndex: 5 }}>
          <AlertTriangle size={18} fill="#eab30822" />
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{data.title || t('node.title_detail')}</strong>
        {data.isEmpty && (
          <span className="tag" style={{ background: 'rgba(239,68,68,0.1)', color: '#dc2626', fontSize: '0.6rem', border: '1px solid rgba(239,68,68,0.2)' }}>EMPTY</span>
        )}
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
        {t('node.type_label')}: {t(`content_type.${data.type}`, { defaultValue: data.type || 'factual' })}
      </div>
      <div className="tag-container" style={{ marginTop: '8px' }}>
        {(data.tags || []).slice(0, 2).map((tag: string) => (
          <span className="tag" key={tag} style={{ fontSize: '0.65rem', padding: '2px 8px' }}>#{tag}</span>
        ))}
      </div>

      {isExpanded && bodyPreview && (
        <div style={{
          marginTop: 8,
          fontSize: '0.65rem',
          color: 'var(--text-muted)',
          lineHeight: 1.5,
          borderTop: '1px solid var(--border-subtle)',
          paddingTop: 6,
          overflow: 'hidden',
          display: '-webkit-box',
          WebkitLineClamp: 2,
          WebkitBoxOrient: 'vertical',
        }}>
          {bodyPreview}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: 'var(--color-primary)' }} />
    </div>
  );
};

export default memo(MemoryNode);
