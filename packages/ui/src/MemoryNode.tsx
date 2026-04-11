import { memo } from 'react';
import { Handle, Position } from 'reactflow';
import { BrainCircuit } from 'lucide-react';

const MemoryNode = ({ data }: { data: any }) => {
  return (
    <div className="glass-panel" style={{ 
      padding: '12px 16px', 
      minWidth: '200px', 
      border: '1px solid var(--border-strong)',
      boxShadow: 'var(--shadow-md)'
    }}>
      <Handle type="target" position={Position.Top} style={{ background: 'var(--color-primary)' }} />
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '8px' }}>
        <BrainCircuit size={16} color="var(--color-primary)" />
        <strong style={{ fontSize: '0.9rem', color: 'var(--text-primary)' }}>{data.title || 'Untitled Memory'}</strong>
      </div>
      <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
        Type: {data.type || 'factual'}
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
