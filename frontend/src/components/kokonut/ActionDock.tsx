import React from 'react';
import { Loader2 } from 'lucide-react';
import type { Scenario } from '../../types';

interface ActionDockProps {
  scenarios: Scenario[];
  isRunning: boolean;
  activeScenario: string | null;
  onRunScenario: (scenarioName: string) => void;
}

export const ActionDock: React.FC<ActionDockProps> = ({
  scenarios,
  isRunning,
  activeScenario,
  onRunScenario,
}) => {
  const getScenarioConfig = (nome: string) => {
    switch (nome) {
      case 'sem_incidente':
        return { label: 'Carga Normal', dot: 'bg-[#8EA89D]' };
      case 'valores_nulos':
        return { label: 'Valores Nulos', dot: 'bg-[#C5A880]' };
      case 'mudanca_estrutura':
        return { label: 'Schema Drift', dot: 'bg-[#C87D6E]' };
      case 'timeout_api':
        return { label: 'Timeout API', dot: 'bg-[#9E9C96]' };
      case 'registros_duplicados':
        return { label: 'Duplicados', dot: 'bg-[#B0A8A0]' };
      case 'tipo_invalido':
        return { label: 'Tipo inválido', dot: 'bg-[#C87D6E]' };
      default:
        return { label: nome.replace('_', ' '), dot: 'bg-[#63615C]' };
    }
  };

  return (
    <div className="w-full">
      <div className="editorial-card p-3 px-4 flex flex-col md:flex-row items-center justify-between gap-3">
        {/* Dock Kicker */}
        <div className="flex items-center gap-2 shrink-0">
          <span className="text-xs font-semibold text-[#F3F2EE]">
            Cenários de laboratório:
          </span>
          <span className="text-[11px] text-[#63615C] hidden sm:inline font-mono-code">
            (dispare cenários para avaliar a reação do pipeline)
          </span>
        </div>

        {/* Buttons */}
        <div className="flex flex-wrap items-center gap-1.5">
          {scenarios.map((sc) => {
            const config = getScenarioConfig(sc.nome);
            const isThisRunning = isRunning && activeScenario === sc.nome;

            return (
              <button
                key={sc.nome}
                onClick={() => onRunScenario(sc.nome)}
                disabled={isRunning}
                className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium text-[#F3F2EE] bg-[#16181D] hover:bg-[#1D2027] border border-white/[0.06] hover:border-white/[0.14] transition-all cursor-pointer disabled:opacity-30 disabled:cursor-not-allowed"
                title={sc.descricao}
              >
                {isThisRunning ? (
                  <Loader2 className="w-3 h-3 animate-spin text-[#8EA89D]" />
                ) : (
                  <span className={`w-1.5 h-1.5 rounded-full ${config.dot}`} />
                )}
                <span>{config.label}</span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
