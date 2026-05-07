import { useState, useEffect, useCallback, useRef } from 'react';
import { api, type NeighborhoodResponse } from '../api';

/**
 * P4.7-S2-1: Hook for fetching and managing neighborhood data (subgraph around a node).
 */
export function useNeighborhood(workspaceId: string, rootNodeId: string | null) {
  const [data, setData] = useState<NeighborhoodResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const lastFetchedId = useRef<string | null>(null);

  const traversalTimeout = useRef<any>(null);

  const fetchNeighborhood = useCallback(async (nodeId: string) => {
    if (!workspaceId || !nodeId) return;
    setLoading(true);
    setError(null);
    try {
      const result = await api.nodes.neighborhood(workspaceId, nodeId, { 
        depth: 2,
        include_source: false // Default to false for better exploration UX
      });
      setData(result);
      lastFetchedId.current = nodeId;
      
      // P4.7-S3-4: Debounced traversal recording (2s)
      if (traversalTimeout.current) clearTimeout(traversalTimeout.current);
      traversalTimeout.current = setTimeout(() => {
        api.nodes.traverse(nodeId).catch(err => {
          console.warn('Failed to record traversal:', err);
        });
      }, 2000);
    } catch (err) {
      console.error('Neighborhood fetch error:', err);
      setError(err as Error);
    } finally {
      setLoading(false);
    }
  }, [workspaceId]);

  useEffect(() => {
    return () => {
      if (traversalTimeout.current) clearTimeout(traversalTimeout.current);
    };
  }, []);

  useEffect(() => {
    if (rootNodeId && rootNodeId !== lastFetchedId.current) {
      fetchNeighborhood(rootNodeId);
    } else if (!rootNodeId) {
      setData(null);
      lastFetchedId.current = null;
    }
  }, [rootNodeId, fetchNeighborhood]);

  return { 
    nodes: data?.nodes || [], 
    edges: data?.edges || [], 
    loading, 
    error, 
    refetch: () => rootNodeId && fetchNeighborhood(rootNodeId) 
  };
}
