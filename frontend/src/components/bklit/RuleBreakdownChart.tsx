import React from 'react';
import type { HistoryRecord } from '../../types';

interface RuleBreakdownProps {
  history: HistoryRecord[];
}

export const RuleBreakdownChart: React.FC<RuleBreakdownProps> = ({ history }) => {
  const rules = [
    { key: 'null_values', label: 'Valores Nulos (Not Null)', match: ['null', 'nulo'] },
    { key: 'schema_drift', label: 'Schema Drift (Colunas)', match: ['schema', 'estrutura', 'column'] },
    { key: 'api_timeout', label: 'Conectividade (Timeout API)', match: ['timeout', 'api'] },
    { key: 'duplicates', label: 'Unicidade de Registros', match: ['duplic', 'duplicate'] },
    { key: 'invalid_type', label: 'Tipagem Numérica', match: ['type', 'tipo', 'invalido'] },
  ];

  const totalRuns = Math.max(1, history.length);

  const stats = rules.map((r) => {
    const failures = history.filter((h) => {
      const s = (h.scenario || '').toLowerCase();
      const summary = (h.summary || '').toLowerCase();
      return r.match.some((m) => s.includes(m) || summary.includes(m)) && h.failed_checks > 0;
    }).length;

    const passes = history.length > 0 ? Math.max(0, totalRuns - failures) : 1;
    const successRate = totalRuns > 0 ? Math.round((passes / totalRuns) * 100) : 100;

    return {
      ...r,
      failures,
      successRate,
    };
  });

  return (
    <div className="editorial-card p-6 flex flex-col justify-between h-full">
      <div className="mb-3">
        <span className="text-[10px] font-mono-code text-[#9E9C96] uppercase tracking-wider">
          Contratos de dados
        </span>
        <h3 className="font-display font-semibold text-sm text-[#F3F2EE] mt-0.5 tracking-tight">
          Status das Regras
        </h3>
      </div>

      <div className="space-y-3.5 my-2">
        {stats.map((rule) => {
          const isPassed = rule.failures === 0;
          return (
            <div key={rule.key} className="space-y-1">
              <div className="flex items-center justify-between text-xs">
                <span className="text-[#F3F2EE]/90 font-normal flex items-center gap-2">
                  <span className={`w-1.5 h-1.5 rounded-full ${isPassed ? 'bg-[#8EA89D]' : 'bg-[#C87D6E]'}`} />
                  {rule.label}
                </span>
                <span className="font-mono-code text-[11px] text-[#63615C]">
                  {rule.failures > 0 ? (
                    <span className="text-[#C87D6E]">{rule.failures} falha(s)</span>
                  ) : (
                    <span className="text-[#8EA89D]/80">100%</span>
                  )}
                </span>
              </div>

              {/* Progress bar */}
              <div className="h-1 w-full bg-[#16181D] rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full ${isPassed ? 'bg-[#8EA89D]/80' : 'bg-[#C87D6E]/80'
                    }`}
                  style={{ width: `${Math.max(5, rule.successRate)}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      <div className="pt-3 border-t border-white/[0.04] text-[11px] text-[#63615C] font-mono-code flex items-center justify-between">
        <span>Pydantic v2 + Great Expectations</span>
        <span>YAML Contracts</span>
      </div>
    </div>
  );
};
