import React, { useState } from 'react';
import type { HistoryRecord } from '../../types';
import { ChevronDown, ChevronUp } from 'lucide-react';

interface AgentCollaborationCardProps {
  latestRecord: HistoryRecord | null;
}

export const AgentCollaborationCard: React.FC<AgentCollaborationCardProps> = ({ latestRecord }) => {
  const [expanded, setExpanded] = useState(false);

  if (!latestRecord) {
    return (
      <div className="editorial-card p-6 flex flex-col items-center justify-center min-h-[200px] text-[#63615C]">
        <p className="text-xs">Nenhuma sessão multiagente registrada até o momento.</p>
      </div>
    );
  }

  const collaboration = latestRecord.collaboration;
  const supervisorDecision = latestRecord.collaboration_summary || collaboration?.supervisor_decision || 'Consenso homologado sem necessidade de intervenção.';
  const dialogue = collaboration?.dialogue || [];
  const engine = latestRecord.diagnosis_engine.replace('_', ' ');
  const isQuarantined = latestRecord.quarantined || latestRecord.failed_checks > 0;

  const agents = [
    { name: 'DataQuality', role: 'Auditoria de Contratos' },
    { name: 'Investigation', role: 'Causa Raiz' },
    { name: 'Supervisor', role: 'Homologação' },
    { name: 'Resolution', role: 'Circuit Breaker' },
  ];

  return (
    <div className="editorial-card p-6 flex flex-col justify-between">
      {/* Top Header */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-[10px] font-mono-code text-[#9E9C96] uppercase tracking-wider">
            Triagem Multiagente Autônoma
          </span>
          <h3 className="font-display font-semibold text-sm text-[#F3F2EE] mt-0.5 tracking-tight">
            Diagnóstico & Consenso
          </h3>
        </div>

        <div className="flex items-center gap-2 text-xs font-mono-code">
          <span className="text-[#63615C]">Engine:</span>
          <span className="text-[#9E9C96] capitalize">{engine}</span>
          <span className="text-white/10">•</span>
          <span className={isQuarantined ? 'text-[#C87D6E] font-medium' : 'text-[#8EA89D] font-medium'}>
            {isQuarantined ? 'Quarentena Ativa' : 'Carga Homologada'}
          </span>
        </div>
      </div>

      {/* Sleek Agent Workflow Line */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 my-2">
        {agents.map((ag, i) => (
          <div
            key={i}
            className="p-3 rounded-lg bg-[#16181D]/60 border border-white/[0.04] flex flex-col justify-between"
          >
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-[#63615C] font-mono-code">0{i + 1}</span>
              <span className="w-1.5 h-1.5 rounded-full bg-[#8EA89D]" />
            </div>
            <div className="mt-2 text-xs font-medium text-[#F3F2EE]">{ag.name}</div>
            <div className="text-[10px] text-[#9E9C96]">{ag.role}</div>
          </div>
        ))}
      </div>

      {/* Decision Summary */}
      <div className="p-3.5 rounded-lg bg-[#16181D]/60 border border-white/[0.04] my-3">
        <div className="text-[10px] uppercase tracking-wider text-[#9E9C96] font-mono-code mb-1">
          Parecer do Supervisor
        </div>
        <p className="text-xs text-[#F3F2EE]/90 leading-relaxed font-sans">{supervisorDecision}</p>
        <div className="mt-2 text-[11px] text-[#63615C] font-mono-code">
          Diagnóstico: <span className="text-[#9E9C96]">{latestRecord.summary}</span>
        </div>
      </div>

      {/* Expand Dialogue Accordion */}
      {dialogue.length > 0 && (
        <div className="pt-2 border-t border-white/[0.04]">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between text-xs text-[#9E9C96] hover:text-[#F3F2EE] transition-colors"
          >
            <span>Transcrição da comunicação multiagente ({dialogue.length} etapas)</span>
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {expanded && (
            <div className="space-y-2 mt-3 max-h-52 overflow-y-auto pr-1 font-mono-code text-[11px]">
              {dialogue.map((turn, i) => (
                <div
                  key={i}
                  className="p-2.5 rounded-md bg-[#0B0C0E]/60 border border-white/[0.04] text-xs text-[#9E9C96]"
                >
                  <div className="flex items-center justify-between text-[10px] text-[#63615C] mb-1">
                    <span className="font-semibold text-[#8EA89D]">{turn.speaker}</span>
                    <span className="uppercase text-[9px]">{turn.action}</span>
                  </div>
                  <p className="text-[#F3F2EE]/80 leading-relaxed font-sans text-xs">{turn.content}</p>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
