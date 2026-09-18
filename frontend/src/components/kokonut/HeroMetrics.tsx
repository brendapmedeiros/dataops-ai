import { Activity, Database, ShieldAlert, ShieldCheck } from 'lucide-react';
import type { GoldRecord, HistoryRecord } from '../../types';

interface HeroMetricsProps {
  goldData: GoldRecord[];
  history: HistoryRecord[];
  onOpenLatestIncident: () => void;
}

function relativeTime(timestamp?: string) {
  if (!timestamp) return 'sem horário registrado';
  const elapsed = Math.max(0, Math.round((Date.now() - new Date(timestamp).getTime()) / 60000));
  if (elapsed < 2) return 'há menos de 2 min';
  if (elapsed < 60) return `há ${elapsed} min`;
  return `há ${Math.floor(elapsed / 60)}h ${elapsed % 60}min`;
}

export function HeroMetrics({ goldData, history, onOpenLatestIncident }: HeroMetricsProps) {
  const latestRun = history[0];
  const quarantined = history.filter((item) => item.quarantined || item.failed_checks > 0);
  const recentRuns = history.slice(0, 12);
  const recentIncidentCount = recentRuns.filter((item) => item.quarantined || item.failed_checks > 0).length;
  const successRate = recentRuns.length ? Math.round(((recentRuns.length - recentIncidentCount) / recentRuns.length) * 100) : null;
  const latestGold = goldData.at(-1);
  const activeIncident = quarantined[0];

  return (
    <section aria-label="Resumo operacional" className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <div className="dash-card p-4">
        <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]"><span>Última execução</span><Activity className="h-4 w-4 text-[var(--info)]" /></div>
        <p className="mt-3 font-data text-xl font-semibold text-[var(--text-primary)]">{latestRun ? (latestRun.failed_checks ? 'Com falha' : 'Concluída') : 'Sem leitura'}</p>
        <p className="mt-1 text-[11px] text-[var(--text-muted)]">{latestRun ? `${relativeTime(latestRun.recorded_at)} · ${latestRun.rows_checked ?? 0} linhas avaliadas` : 'Aguardando histórico da API'}</p>
      </div>

      <div className="dash-card p-4">
        <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]"><span>Qualidade · últimas 12 runs</span><ShieldCheck className="h-4 w-4 text-[var(--accent)]" /></div>
        <p className="mt-3 font-data text-xl font-semibold text-[var(--text-primary)]">{successRate === null ? '—' : `${successRate}%`}</p>
        <p className="mt-1 text-[11px] text-[var(--text-muted)]">{recentRuns.length ? `${recentRuns.length - recentIncidentCount} aprovadas · meta ≥ 99%` : 'Ainda não há amostra suficiente'}</p>
      </div>

      <div className="dash-card p-4">
        <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]"><span>Freshness da Gold</span><Database className="h-4 w-4 text-[var(--accent)]" /></div>
        <p className="mt-3 font-data text-xl font-semibold text-[var(--text-primary)]">{latestGold?.date ?? '—'}</p>
        <p className="mt-1 text-[11px] text-[var(--text-muted)]">{latestGold ? `Série ${latestGold.series_code} · ${goldData.length} registros carregados` : 'Nenhum dado homologado retornado'}</p>
      </div>

      <div className={`dash-card p-4 ${activeIncident ? 'border-[color:rgba(220,131,120,.35)]' : ''}`}>
        <div className="flex items-center justify-between text-xs text-[var(--text-secondary)]"><span>Incidentes ativos</span><ShieldAlert className={`h-4 w-4 ${activeIncident ? 'text-[var(--danger)]' : 'text-[var(--accent)]'}`} /></div>
        <div className="mt-3 flex items-baseline justify-between gap-3"><p className={`font-data text-xl font-semibold ${activeIncident ? 'text-[var(--danger)]' : 'text-[var(--text-primary)]'}`}>{quarantined.length}</p>{activeIncident && <button onClick={onOpenLatestIncident} className="text-[11px] font-medium text-[var(--accent-strong)] hover:underline">Abrir triagem</button>}</div>
        <p className="mt-1 text-[11px] text-[var(--text-muted)]">{activeIncident ? `${activeIncident.severity.toUpperCase()} · ${activeIncident.scenario.replaceAll('_', ' ')}` : 'Nenhuma ação operacional pendente'}</p>
      </div>
    </section>
  );
}
