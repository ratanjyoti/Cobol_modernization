import { ProjectAPI } from './api';
import type { DependencyRelation, FileRecord } from './api';

export type AnalysisWarmCache = {
  complexity?: any;
  graph?: any;
  ddd?: any[];
  files?: FileRecord[];
  relations?: DependencyRelation[];
  updatedAt: number;
};

const cacheByRun = new Map<string, AnalysisWarmCache>();
const warmupsByRun = new Map<string, Promise<AnalysisWarmCache>>();
const discoveryWarmupsByRun = new Map<string, Promise<AnalysisWarmCache>>();
const retryWarmupsByRun = new Map<string, number>();

const mergeCache = (runId: string, partial: Partial<AnalysisWarmCache>) => {
  const current = cacheByRun.get(runId) || { updatedAt: 0 };
  const next = { ...current, ...partial, updatedAt: Date.now() };
  cacheByRun.set(runId, next);
  return next;
};

export const getAnalysisWarmCache = (runId?: string | null) => {
  if (!runId) return null;
  return cacheByRun.get(runId) || null;
};

export const clearAnalysisWarmCache = (runId?: string | null) => {
  if (!runId) return;
  cacheByRun.delete(runId);
  warmupsByRun.delete(runId);
  discoveryWarmupsByRun.delete(runId);
  const retryTimer = retryWarmupsByRun.get(runId);
  if (retryTimer) {
    window.clearTimeout(retryTimer);
    retryWarmupsByRun.delete(runId);
  }
};

export const warmDiscoveryData = (runId?: string | null, force = false) => {
  if (!runId) {
    return Promise.resolve({ updatedAt: Date.now() } as AnalysisWarmCache);
  }

  const existingWarmup = discoveryWarmupsByRun.get(runId);
  if (existingWarmup && !force) return existingWarmup;

  const warmup = ProjectAPI.getDiscoveryData(runId).then((data) => {
    return mergeCache(runId, {
      files: data.files || [],
      relations: data.relations || [],
    });
  }).finally(() => {
    discoveryWarmupsByRun.delete(runId);
  });

  discoveryWarmupsByRun.set(runId, warmup);
  return warmup;
};

export const warmAnalysisTabs = (runId?: string | null, force = false) => {
  if (!runId) {
    return Promise.resolve({ updatedAt: Date.now() } as AnalysisWarmCache);
  }

  const existingWarmup = warmupsByRun.get(runId);
  if (existingWarmup && !force) return existingWarmup;

  const warmup = Promise.allSettled([
    ProjectAPI.getComplexity(runId),
    ProjectAPI.getGraph(runId),
    ProjectAPI.getDDD(runId),
    ProjectAPI.getDiscoveryData(runId),
  ]).then((results) => {
    const [complexity, graph, ddd, discovery] = results;
    const partial: Partial<AnalysisWarmCache> = {};

    if (complexity.status === 'fulfilled') partial.complexity = complexity.value;
    if (graph.status === 'fulfilled') partial.graph = graph.value;
    if (ddd.status === 'fulfilled') partial.ddd = ddd.value || [];
    if (discovery.status === 'fulfilled') {
      partial.files = discovery.value.files || [];
      partial.relations = discovery.value.relations || [];
    }

    return mergeCache(runId, partial);
  }).finally(() => {
    warmupsByRun.delete(runId);
  });

  warmupsByRun.set(runId, warmup);
  return warmup;
};

const hasUsefulAnalysisData = (cache: AnalysisWarmCache) => {
  const filesReady = (cache.files?.length || 0) > 0;
  const complexityReady = (cache.complexity?.files?.length || 0) > 0;
  const graphReady = (cache.graph?.nodes?.length || 0) > 0;
  const dddReady = (cache.ddd?.length || 0) > 0;
  return filesReady && (complexityReady || graphReady || dddReady);
};

export const warmAnalysisTabsWithRetry = (
  runId?: string | null,
  options: { attempts?: number; delayMs?: number } = {},
) => {
  if (!runId) return;

  const attempts = options.attempts ?? 18;
  const delayMs = options.delayMs ?? 3000;

  const retryTimer = retryWarmupsByRun.get(runId);
  if (retryTimer) window.clearTimeout(retryTimer);

  const runAttempt = async (remainingAttempts: number) => {
    try {
      const cache = await warmAnalysisTabs(runId, true);
      if (hasUsefulAnalysisData(cache) || remainingAttempts <= 1) {
        retryWarmupsByRun.delete(runId);
        return;
      }
    } catch (error) {
      console.warn('Analysis warmup retry failed:', error);
      if (remainingAttempts <= 1) {
        retryWarmupsByRun.delete(runId);
        return;
      }
    }

    const timer = window.setTimeout(() => {
      void runAttempt(remainingAttempts - 1);
    }, delayMs);
    retryWarmupsByRun.set(runId, timer);
  };

  void runAttempt(attempts);
};
