import type { SystemStatus, Scenario, HistoryRecord, GoldRecord, QuarantineBatch, RunResult } from '../types';

const API_BASE = import.meta.env.VITE_API_URL || '/api';

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const res = await fetch(`${API_BASE}/status`);
  if (!res.ok) throw new Error('Status operacional indisponível');
  return await res.json();
}

export async function fetchScenarios(): Promise<Scenario[]> {
  const res = await fetch(`${API_BASE}/cenarios`);
  if (!res.ok) throw new Error('Cenários de laboratório indisponíveis');
  const data = await res.json();
  return data.cenarios || [];
}

export async function fetchHistory(limit = 20): Promise<HistoryRecord[]> {
  const res = await fetch(`${API_BASE}/historico?limit=${limit}`);
  if (!res.ok) throw new Error('Histórico de execuções indisponível');
  const data = await res.json();
  return data.historico || [];
}

export async function fetchGoldData(limit = 100): Promise<{ total: number; registros: GoldRecord[] }> {
  const res = await fetch(`${API_BASE}/dados/gold?limit=${limit}`);
  if (!res.ok) throw new Error('Camada Gold indisponível');
  return await res.json();
}

export async function fetchQuarantineData(): Promise<{ total_lotes: number; lotes: QuarantineBatch[] }> {
  const res = await fetch(`${API_BASE}/dados/quarentena`);
  if (!res.ok) throw new Error('Fila de quarentena indisponível');
  return await res.json();
}

export async function triggerPipelineRun(scenario: string): Promise<RunResult> {
  const res = await fetch(`${API_BASE}/execucoes`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ scenario }),
  });

  if (!res.ok) {
    const errorBody = await res.json().catch(() => ({ detail: 'Erro na execução da pipeline' }));
    throw new Error(errorBody.detail || 'Erro ao disparar pipeline');
  }

  return await res.json();
}
