import { memo } from 'react';
import { useTranslation } from 'react-i18next';
import { Handle, Position } from 'reactflow';
import { AlertTriangle } from 'lucide-react';

const MemoryNode = ({ data }: { data: any }) => {
  const { t } = useTranslation();
  const isExpired = data.validityExpired;

  return (
    <div
      className="glass-panel"
      title={data.healthTooltip || undefined}
      style={{
        padding: '12px 16px',
        minWidth: '200px',
        border: `1px solid ${data.healthColor || 'var(--border-strong)'}`,
        boxShadow: data.healthColor ? `0 0 0 1px ${data.healthColor}40, var(--shadow-md)` : 'var(--shadow-md)',
        background: data.healthColor ? `color-mix(in srgb, ${data.healthColor} 8%, var(--bg-surface))` : undefined,
        position: 'relative',
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
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
        {t('node.type_label')}: {t(`content_type.${data.type}`, { defaultValue: data.type || 'factual' })}
      </div>
      <div className="tag-container" style={{ marginTop: '8px' }}>
        {(data.tags || []).slice(0, 2).map((tag: string) => (
          <span className="tag" key={tag} style={{ fontSize: '0.65rem', padding: '2px 8px' }}>#{tag}</span>
        ))}
      </div>
      <Handle type="source" position={Position.Bottom} style={{ background: 'var(--color-primary)' }} />
    </div>
  );
};

export default memo(MemoryNode);
