import { useCallback, useEffect, useMemo, useState } from 'react';
import { AlertTriangle, CheckCircle2, ExternalLink, FlaskConical } from 'lucide-react';
import { fetchGoldData, fetchHistory, fetchQuarantineData, fetchScenarios, fetchSystemStatus, triggerPipelineRun } from './services/api';
import type { GoldRecord, HistoryRecord, QuarantineBatch, RunResult, Scenario, SystemStatus } from './types';
import { StatusHeader } from './components/kokonut/StatusHeader';
import { HeroMetrics } from './components/kokonut/HeroMetrics';
import { ActionDock } from './components/kokonut/ActionDock';
import { AgentCollaborationCard } from './components/kokonut/AgentCollaborationCard';
import { AuditSheet } from './components/kokonut/AuditSheet';
import { TimeSeriesAreaChart } from './components/bklit/TimeSeriesAreaChart';
import { HealthGauge } from './components/bklit/HealthGauge';
import { RuleBreakdownChart } from './components/bklit/RuleBreakdownChart';
import { GoldDataTable } from './components/data/GoldDataTable';
import { QuarantineViewer } from './components/data/QuarantineViewer';
import { IncidentHistoryTable } from './components/data/IncidentHistoryTable';

type Tab = 'cockpit' | 'history' | 'gold' | 'quarantine' | 'lab';

function auditRecordFromRun(result: RunResult): HistoryRecord {
  return {
    run_id: result.run_id,
    scenario: result.cenario,
    rows_checked: result.linhas_carregadas,
    failed_checks: result.validacoes_com_falha,
    severity: result.gravidade,
    diagnosis_engine: result.motor_do_diagnostico,
    quarantined: result.quarentenado,
    audit_hash: result.audit_hash,
    collaboration_status: result.collaboration_status,
    collaboration_summary: result.collaboration_summary,
    collaboration: result.collaboration,
    requires_manual_review: result.precisa_revisao_manual,
    summary: result.resumo,
  };
}

export function App() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [history, setHistory] = useState<HistoryRecord[]>([]);
  const [goldData, setGoldData] = useState<GoldRecord[]>([]);
  const [quarantineBatches, setQuarantineBatches] = useState<QuarantineBatch[]>([]);
  const [activeTab, setActiveTab] = useState<Tab>('cockpit');
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [lastResult, setLastResult] = useState<RunResult | null>(null);
  const [selectedAuditRecord, setSelectedAuditRecord] = useState<HistoryRecord | null>(null);
  const [sourcesUnavailable, setSourcesUnavailable] = useState<string[]>([]);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const refreshData = useCallback(async () => {
    setIsRefreshing(true);
    const labels = ['status', 'cenários', 'histórico', 'Gold', 'quarentena'];
    try {
      const results = await Promise.allSettled([fetchSystemStatus(), fetchScenarios(), fetchHistory(100), fetchGoldData(250), fetchQuarantineData()]);
      const unavailable = results.flatMap((result, index) => result.status === 'rejected' ? [labels[index]] : []);
      setSourcesUnavailable(unavailable);
      if (results[0].status === 'fulfilled') setStatus(results[0].value);
      if (results[1].status === 'fulfilled') setScenarios(results[1].value);
      if (results[2].status === 'fulfilled') setHistory(results[2].value);
      if (results[3].status === 'fulfilled') setGoldData(results[3].value.registros || []);
      if (results[4].status === 'fulfilled') setQuarantineBatches(results[4].value.lotes || []);
      setLastUpdated(new Date());
    } finally {
      setIsRefreshing(false);
    }
  }, []);

  useEffect(() => {
    const id = window.setTimeout(() => { void refreshData(); }, 0);
    return () => window.clearTimeout(id);
  }, [refreshData]);
  useEffect(() => {
    const id = window.setInterval(() => { if (!isRunning) void refreshData(); }, 60_000);
    return () => window.clearInterval(id);
  }, [isRunning, refreshData]);

  const handleRunScenario = async (scenarioName: string) => {
    setIsRunning(true);
    setActiveScenario(scenarioName);
    setLastResult(null);
    try {
      const result = await triggerPipelineRun(scenarioName);
      setLastResult(result);
      setActiveTab('cockpit');
      await refreshData();
    } catch {
      setSourcesUnavailable((current) => Array.from(new Set([...current, 'execução de laboratório'])));
    } finally {
      setIsRunning(false);
      setActiveScenario(null);
    }
  };

  const quarantinedRuns = useMemo(() => history.filter((item) => item.quarantined || item.failed_checks > 0), [history]);
  const latestIncident = quarantinedRuns[0] ?? null;
  const healthScore = history.length ? Math.max(0, Math.round(((history.length - quarantinedRuns.length) / history.length) * 100)) : 100;
  const latestRecord = history[0] ?? null;
  const labEnabled = import.meta.env.DEV || import.meta.env.VITE_ENABLE_LAB === 'true';
  const tabs: Array<{ id: Tab; label: string; count?: number }> = [
    { id: 'cockpit', label: 'Cockpit' },
    { id: 'history', label: 'Incidentes', count: history.length },
    { id: 'gold', label: 'Camada Gold', count: goldData.length },
    { id: 'quarantine', label: 'DLQ', count: quarantineBatches.length },
    ...(labEnabled ? [{ id: 'lab' as Tab, label: 'Laboratório' }] : []),
  ];

  return (
    <div className="relative flex min-h-screen flex-col overflow-x-hidden bg-[var(--bg-app)] text-[var(--text-primary)]">
      <div className="ambient-editorial" />
      <StatusHeader status={status} history={history} isRefreshing={isRefreshing} lastUpdated={lastUpdated} sourcesUnavailable={sourcesUnavailable} onRefresh={() => void refreshData()} />

      <main className="relative z-10 mx-auto flex w-full max-w-6xl flex-1 flex-col gap-6 px-5 py-7 sm:px-6">
        {sourcesUnavailable.length > 0 && (
          <div role="alert" className="flex flex-col gap-3 rounded-xl border border-[color:rgba(217,173,101,.32)] bg-[color:rgba(217,173,101,.09)] p-4 text-sm sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-start gap-3"><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-[var(--warning)]" /><div><p className="font-medium text-[var(--text-primary)]">Dados parcialmente indisponíveis</p><p className="mt-0.5 text-xs text-[var(--text-secondary)]">Não inferimos status saudável quando uma fonte falha. Verifique: {sourcesUnavailable.join(', ')}.</p></div></div>
            <button onClick={() => void refreshData()} className="self-start text-xs font-medium text-[var(--accent-strong)] hover:underline sm:self-auto">Tentar novamente</button>
          </div>
        )}

        <HeroMetrics goldData={goldData} history={history} onOpenLatestIncident={() => latestIncident && setSelectedAuditRecord(latestIncident)} />

        {latestIncident ? (
          <section className="editorial-card flex flex-col gap-4 border-[color:rgba(220,131,120,.30)] p-5 md:flex-row md:items-center md:justify-between" aria-label="Incidente que exige atenção">
            <div className="flex items-start gap-3"><span className="status-dot status-dot--danger mt-1.5" /><div><p className="text-xs font-semibold uppercase tracking-wide text-[var(--danger)]">Ação necessária · {latestIncident.severity}</p><h1 className="mt-1 text-base font-semibold">{latestIncident.summary || 'Lote em quarentena requer triagem'}</h1><p className="mt-1 text-xs text-[var(--text-secondary)]">Run #{latestIncident.run_id.slice(0, 8)} · cenário {latestIncident.scenario.replaceAll('_', ' ')} · {latestIncident.failed_checks} contrato(s) falharam</p></div></div>
            <div className="flex shrink-0 gap-2"><button onClick={() => setSelectedAuditRecord(latestIncident)} className="rounded-lg bg-[var(--accent)] px-3 py-2 text-xs font-semibold text-[#0b0d12] hover:bg-[var(--accent-strong)]">Abrir triagem</button><button onClick={() => setActiveTab('quarantine')} className="rounded-lg border border-[var(--border-strong)] px-3 py-2 text-xs font-medium text-[var(--text-primary)] hover:bg-[var(--bg-hover)]">Ver DLQ</button></div>
          </section>
        ) : (
          <section className="flex items-center gap-3 rounded-xl border border-[color:rgba(143,183,161,.24)] bg-[color:rgba(143,183,161,.07)] px-4 py-3 text-sm"><CheckCircle2 className="h-4 w-4 text-[var(--accent)]" /><span>Sem incidentes ativos: a camada Gold está protegida pelos contratos atuais.</span></section>
        )}

        {lastResult && <div className={`flex flex-col gap-3 rounded-xl border p-4 text-sm sm:flex-row sm:items-center sm:justify-between ${lastResult.quarentenado ? 'border-[color:rgba(220,131,120,.30)] bg-[color:rgba(220,131,120,.08)]' : 'border-[color:rgba(143,183,161,.25)] bg-[color:rgba(143,183,161,.07)]'}`}><p><strong>{lastResult.quarentenado ? 'Execução isolada.' : 'Execução concluída.'}</strong> <span className="text-[var(--text-secondary)]">{lastResult.resumo}</span></p><button onClick={() => setSelectedAuditRecord(auditRecordFromRun(lastResult))} className="inline-flex items-center gap-1 text-xs font-medium text-[var(--accent-strong)] hover:underline">Abrir auditoria <ExternalLink className="h-3 w-3" /></button></div>}

        <nav className="flex gap-1 overflow-x-auto border-b border-[var(--border-app)] pb-2" aria-label="Áreas do dashboard">
          {tabs.map((tab) => <button key={tab.id} type="button" onClick={() => setActiveTab(tab.id)} aria-current={activeTab === tab.id ? 'page' : undefined} className={`whitespace-nowrap rounded-lg px-3 py-2 text-xs font-medium transition-colors ${activeTab === tab.id ? 'bg-[var(--bg-subtle)] text-[var(--text-primary)]' : 'text-[var(--text-secondary)] hover:bg-[var(--bg-subtle)] hover:text-[var(--text-primary)]'}`}>{tab.label}{tab.count !== undefined && <span className="ml-1.5 font-mono-code text-[10px] text-[var(--text-muted)]">{tab.count}</span>}</button>)}
        </nav>

        {activeTab === 'cockpit' && <div className="space-y-6"><div className="grid grid-cols-1 gap-6 lg:grid-cols-3"><div className="lg:col-span-2"><TimeSeriesAreaChart data={goldData} /></div><HealthGauge score={healthScore} totalRuns={history.length} quarantinedRuns={quarantinedRuns.length} /></div><div className="grid grid-cols-1 gap-6 lg:grid-cols-3"><div className="lg:col-span-2"><AgentCollaborationCard latestRecord={latestRecord} /></div><RuleBreakdownChart history={history} /></div></div>}
        {activeTab === 'history' && <IncidentHistoryTable history={history} onSelectAudit={setSelectedAuditRecord} />}
        {activeTab === 'gold' && <GoldDataTable data={goldData} />}
        {activeTab === 'quarantine' && <QuarantineViewer batches={quarantineBatches} />}
        {activeTab === 'lab' && labEnabled && <section className="space-y-3"><div className="flex items-start gap-3 rounded-xl border border-[color:rgba(123,167,219,.3)] bg-[color:rgba(123,167,219,.08)] p-4"><FlaskConical className="mt-0.5 h-4 w-4 text-[var(--info)]" /><div><p className="text-sm font-semibold">Laboratório de resiliência</p><p className="mt-1 text-xs leading-relaxed text-[var(--text-secondary)]">Use cenários apenas em ambiente autorizado. Em produção, esta ação deve depender de RBAC, justificativa e trilha de auditoria no backend.</p></div></div><ActionDock scenarios={scenarios} isRunning={isRunning} activeScenario={activeScenario} onRunScenario={handleRunScenario} /></section>}
      </main>

      <AuditSheet record={selectedAuditRecord} isOpen={Boolean(selectedAuditRecord)} onClose={() => setSelectedAuditRecord(null)} />
      <footer className="relative z-10 mt-10 border-t border-[var(--border-app)] py-6"><div className="mx-auto flex max-w-6xl flex-col gap-1 px-6 text-[11px] text-[var(--text-muted)] sm:flex-row sm:items-center sm:justify-between"><span>DataOps AI · Observabilidade e governança de dados</span><span className="font-mono-code">FastAPI · React · TypeScript · SHA-256</span></div></footer>
    </div>
  );
}

export default App;
