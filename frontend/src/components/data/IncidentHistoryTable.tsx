import React, { useMemo, useState } from 'react';
import type { HistoryRecord } from '../../types';
import { Lock } from 'lucide-react';

interface IncidentHistoryTableProps {
  history: HistoryRecord[];
  onSelectAudit: (record: HistoryRecord) => void;
}

export const IncidentHistoryTable: React.FC<IncidentHistoryTableProps> = ({
  history,
  onSelectAudit,
}) => {
  const [query, setQuery] = useState('');
  const [severity, setSeverity] = useState('all');
  const filteredHistory = useMemo(() => history.filter((row) => {
    const queryMatches = `${row.run_id} ${row.scenario} ${row.summary}`.toLowerCase().includes(query.toLowerCase());
    return queryMatches && (severity === 'all' || row.severity === severity);
  }), [history, query, severity]);

  return (
    <div className="editorial-card p-6">
      <div className="flex flex-col justify-between gap-4 mb-4 sm:flex-row sm:items-end">
        <div>
          <span className="text-[10px] font-mono-code text-[#9E9C96] uppercase tracking-wider">
            Auditoria Operacional
          </span>
          <h3 className="font-display font-semibold text-sm text-[#F3F2EE] mt-0.5 tracking-tight">
            Trilha de Execuções e Intervenções
          </h3>
        </div>
        <span className="text-xs text-[#9E9C96] font-mono-code">
          {filteredHistory.length} de {history.length} runs
        </span>
      </div>

      <div className="mb-4 flex flex-col gap-2 sm:flex-row">
        <input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar run, cenário ou resumo" className="w-full rounded-lg border border-[var(--border-app)] bg-[var(--bg-subtle)] px-3 py-2 text-xs text-[var(--text-primary)] placeholder:text-[var(--text-muted)] sm:max-w-xs" aria-label="Buscar incidentes" />
        <select value={severity} onChange={(event) => setSeverity(event.target.value)} className="rounded-lg border border-[var(--border-app)] bg-[var(--bg-subtle)] px-3 py-2 text-xs text-[var(--text-primary)]" aria-label="Filtrar por severidade">
          <option value="all">Todas as severidades</option>
          <option value="critical">Crítica</option>
          <option value="high">Alta</option>
          <option value="medium">Média</option>
          <option value="low">Baixa</option>
        </select>
      </div>

      <div className="w-full overflow-x-auto rounded-lg border border-white/[0.04]">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#16181D]/40 text-[#9E9C96] uppercase font-mono-code text-[10px] tracking-wider border-b border-white/[0.04]">
            <tr>
              <th className="py-2.5 px-4 font-normal">Run ID</th>
              <th className="py-2.5 px-4 font-normal">Cenário</th>
              <th className="py-2.5 px-4 font-normal">Falhas</th>
              <th className="py-2.5 px-4 font-normal">Gravidade</th>
              <th className="py-2.5 px-4 font-normal">Motor IA</th>
              <th className="py-2.5 px-4 font-normal">Ação Circuit Breaker</th>
              <th className="py-2.5 px-4 font-normal text-right">Auditoria</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04] text-[#F3F2EE]/90 font-mono-code">
            {filteredHistory.length === 0 ? (
              <tr>
                <td colSpan={7} className="py-8 text-center text-[#63615C] font-sans">
                  Nenhuma execução corresponde aos filtros.
                </td>
              </tr>
            ) : (
              filteredHistory.map((row) => {
                const isQuarantined = row.quarantined || row.failed_checks > 0;
                return (
                  <tr key={row.run_id} className="hover:bg-white/[0.02] transition-colors">
                    <td className="py-2.5 px-4 font-medium text-[#F3F2EE]">
                      #{row.run_id.slice(0, 8)}
                    </td>
                    <td className="py-2.5 px-4 text-[#F3F2EE]/80 font-sans capitalize">
                      {row.scenario.replace('_', ' ')}
                    </td>
                    <td className="py-2.5 px-4">
                      {row.failed_checks > 0 ? (
                        <span className="text-[#C87D6E] font-semibold">{row.failed_checks}</span>
                      ) : (
                        <span className="text-[#63615C]">0</span>
                      )}
                    </td>
                    <td className="py-2.5 px-4 font-sans">
                      <span
                        className={`text-[10px] px-2 py-0.5 rounded uppercase font-mono-code ${row.severity === 'critical'
                            ? 'text-[#C87D6E] bg-[#C87D6E]/10'
                            : row.severity === 'high'
                              ? 'text-[#C5A880] bg-[#C5A880]/10'
                              : 'text-[#9E9C96] bg-white/[0.03]'
                          }`}
                      >
                        {row.severity}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-[#63615C] text-[11px]">
                      {row.diagnosis_engine.replace('_', ' ')}
                    </td>
                    <td className="py-2.5 px-4">
                      <span
                        className={`text-[11px] font-sans ${isQuarantined ? 'text-[#C87D6E]' : 'text-[#8EA89D]'
                          }`}
                      >
                        {isQuarantined ? '● Quarentena (DLQ)' : '● Homologado'}
                      </span>
                    </td>
                    <td className="py-2.5 px-4 text-right">
                      <button
                        onClick={() => onSelectAudit(row)}
                        className="inline-flex items-center gap-1.5 px-2 py-1 rounded bg-[#16181D] hover:bg-[#1D2027] text-[#9E9C96] hover:text-[#F3F2EE] border border-white/[0.06] text-[10px] font-mono-code transition-colors"
                      >
                        <Lock className="w-2.5 h-2.5 text-[#C5A880]" />
                        <span>SHA-256</span>
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
