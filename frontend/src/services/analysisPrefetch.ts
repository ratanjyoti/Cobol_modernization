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
    ProjectAPI.listFiles(runId),
    ProjectAPI.listRelations(runId),
  ]).then((results) => {
    const [complexity, graph, ddd, files, relations] = results;
    const partial: Partial<AnalysisWarmCache> = {};

    if (complexity.status === 'fulfilled') partial.complexity = complexity.value;
    if (graph.status === 'fulfilled') partial.graph = graph.value;
    if (ddd.status === 'fulfilled') partial.ddd = ddd.value || [];
    if (files.status === 'fulfilled') partial.files = files.value.files || [];
    if (relations.status === 'fulfilled') partial.relations = relations.value.relations || [];

    return mergeCache(runId, partial);
  }).finally(() => {
    warmupsByRun.delete(runId);
  });

  warmupsByRun.set(runId, warmup);
  return warmup;
};
