import { useState, useEffect } from 'react';
import { ai } from '../api';

export interface ModelOption {
  id: string;
  dim: number;
  provider: string;
}

const KNOWN_EMBED_MODELS: Record<string, { id: string; dim: number }[]> = {
  openai: [
    { id: 'text-embedding-3-small', dim: 1536 },
    { id: 'text-embedding-3-large', dim: 3072 },
    { id: 'text-embedding-ada-002', dim: 1536 },
  ],
  gemini: [
    { id: 'text-embedding-004', dim: 768 },
  ],
};

export function useProviderModels(type: 'chat' | 'embedding' = 'embedding') {
  const [models, setModels] = useState<ModelOption[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      setLoading(true);
      try {
        const [credits] = await Promise.all([
          ai.getCredits(),
          ai.getResolvedModel(type).catch(() => ({ provider: null, model: null }))
        ]);

        const activeProviders = Object.entries(credits.has_own_key)
          .filter(([_, has]) => has)
          .map(([p]) => p);
        
        const allModels: ModelOption[] = [];
        
        for (const p of activeProviders) {
          if (p === 'anthropic' && type === 'embedding') continue;
          try {
            const fetchedModels = await ai.listModels(p);
            const filtered = fetchedModels.filter(m => m.model_type === type);
            if (filtered.length > 0) {
              allModels.push(...filtered.map(m => ({ 
                id: m.id, 
                dim: m.embedding_dim ?? (KNOWN_EMBED_MODELS[p]?.find(k => k.id === m.id)?.dim ?? 768), 
                provider: p 
              })));
              continue;
            }
          } catch (e) {
            console.warn(`Failed to fetch models for ${p}`, e);
          }
          
          if (type === 'embedding') {
            const known = KNOWN_EMBED_MODELS[p] || [];
            allModels.push(...known.map(m => ({ ...m, provider: p })));
          }
        }

        if (allModels.length === 0 && type === 'embedding') {
          allModels.push({ id: 'text-embedding-3-small', dim: 1536, provider: 'openai' });
        }

        if (mounted) {
          setModels(allModels);
          setError(null);
        }
      } catch (err: any) {
        if (mounted) {
          setError(err.message);
          if (type === 'embedding') {
            setModels([{ id: 'text-embedding-3-small', dim: 1536, provider: 'openai' }]);
          }
        }
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();
    return () => { mounted = false; };
  }, [type]);

  return { models, loading, error };
}
