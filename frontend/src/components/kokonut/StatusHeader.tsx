import { RefreshCw, ShieldAlert, ShieldCheck } from 'lucide-react';
import type { HistoryRecord, SystemStatus } from '../../types';

interface StatusHeaderProps {
  status: SystemStatus | null;
  history: HistoryRecord[];
  isRefreshing: boolean;
  lastUpdated: Date | null;
  sourcesUnavailable: string[];
  onRefresh: () => void;
}

function formatUpdatedAt(date: Date | null) {
  if (!date) return 'Aguardando primeira leitura';
  return new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit', second: '2-digit' }).format(date);
}

export function StatusHeader({ status, history, isRefreshing, lastUpdated, sourcesUnavailable, onRefresh }: StatusHeaderProps) {
  const quarantinedCount = history.filter((item) => item.quarantined || item.failed_checks > 0).length;
  const hasUnavailableSource = sourcesUnavailable.length > 0;
  const needsAttention = quarantinedCount > 0 || hasUnavailableSource;
  const dbOk = status?.banco?.conectado;
  const apiOk = status?.api_banco_central?.available;

  return (
    <header className="sticky top-0 z-40 w-full border-b border-[var(--border-app)] bg-[color:rgba(255,255,255,.88)] backdrop-blur-xl">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-4 px-6">
        <div className="flex min-w-0 items-center gap-3">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-[var(--border-app)] bg-[var(--bg-subtle)]">
            {needsAttention ? <ShieldAlert className="h-4 w-4 text-[var(--warning)]" /> : <ShieldCheck className="h-4 w-4 text-[var(--accent)]" />}
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <span className="font-display text-sm font-semibold tracking-tight text-[var(--text-primary)]">DataOps AI</span>
              <span className="hidden text-xs text-[var(--text-muted)] sm:inline">/ monitoramento diário</span>
            </div>
            <p className="mt-0.5 text-[10px] text-[var(--text-muted)]">Atualizado às {formatUpdatedAt(lastUpdated)} · BRT</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <div className="hidden items-center gap-3 text-[11px] font-mono-code text-[var(--text-secondary)] md:flex">
            <span className={dbOk === false ? 'text-[var(--danger)]' : ''}>DB {dbOk === false ? 'OFF' : 'OK'}</span>
            <span className="text-[var(--border-strong)]">•</span>
            <span className={apiOk === false ? 'text-[var(--danger)]' : ''}>BCB {apiOk === false ? 'OFF' : 'OK'}</span>
          </div>
          <div className={`hidden items-center gap-2 rounded-full border px-2.5 py-1 text-[11px] sm:flex ${needsAttention ? 'border-[color:rgba(217,173,101,.28)] bg-[color:rgba(217,173,101,.08)] text-[var(--warning)]' : 'border-[color:rgba(143,183,161,.22)] bg-[color:rgba(143,183,161,.08)] text-[var(--accent-strong)]'}`}>
            <span className={`status-dot ${needsAttention ? 'status-dot--warning' : 'status-dot--healthy'}`} />
            {hasUnavailableSource ? 'Dados parcialmente indisponíveis' : quarantinedCount > 0 ? `${quarantinedCount} lote(s) exigem atenção` : 'Operação saudável'}
          </div>
          <button onClick={onRefresh} disabled={isRefreshing} className="rounded-lg p-2 text-[var(--text-secondary)] transition-colors hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)] disabled:cursor-wait disabled:opacity-50" aria-label="Atualizar dados">
            <RefreshCw className={`h-4 w-4 ${isRefreshing ? 'animate-spin text-[var(--accent-strong)]' : ''}`} />
          </button>
        </div>
      </div>
    </header>
  );
}
