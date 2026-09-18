import React from 'react';
import type { QuarantineBatch } from '../../types';
import { Archive, CheckCircle2 } from 'lucide-react';

interface QuarantineViewerProps {
  batches: QuarantineBatch[];
}

export const QuarantineViewer: React.FC<QuarantineViewerProps> = ({ batches }) => {
  if (batches.length === 0) {
    return (
      <div className="editorial-card p-10 flex flex-col items-center justify-center text-center">
        <CheckCircle2 className="w-8 h-8 text-[#8EA89D] mb-3 stroke-[1.5]" />
        <h3 className="font-display font-semibold text-sm text-[#F3F2EE] mb-1">
          Quarentena Vazia (Circuit Breaker Saudável)
        </h3>
        <p className="text-xs text-[#9E9C96] max-w-sm mx-auto leading-relaxed">
          Nenhum lote foi isolado pela camada de governança. Todos os contratos de qualidade foram rigorosamente validados.
        </p>
      </div>
    );
  }

  return (
    <div className="editorial-card p-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-[10px] font-mono-code text-[#9E9C96] uppercase tracking-wider">
            Dead Letter Queue (DLQ)
          </span>
          <h3 className="font-display font-semibold text-sm text-[#F3F2EE] mt-0.5 tracking-tight">
            Lotes Isolados pelo Circuit Breaker
          </h3>
        </div>
        <span className="text-xs text-[#C87D6E] font-mono-code">
          {batches.length} lote(s) retido(s)
        </span>
      </div>

      <div className="space-y-2">
        {batches.map((b, idx) => (
          <div
            key={idx}
            className="p-3.5 rounded-lg bg-[#16181D]/60 border border-[#C87D6E]/20 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
          >
            <div className="flex items-center gap-3">
              <Archive className="w-4 h-4 text-[#C87D6E] shrink-0 stroke-[1.5]" />
              <div>
                <div className="text-xs font-medium text-[#F3F2EE] font-mono-code">{b.arquivo}</div>
                <div className="text-[11px] text-[#9E9C96] mt-0.5 flex gap-4 font-mono-code">
                  <span>Isolado: {b.isolado_em.slice(0, 19).replace('T', ' ')}</span>
                  <span>{b.tamanho_bytes} bytes</span>
                </div>
              </div>
            </div>

            <div className="self-end sm:self-center">
              <span className="text-xs font-mono-code text-[#C87D6E]">
                {b.linhas_rejeitadas} linhas retidas
              </span>
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 pt-3 border-t border-white/[0.04] flex items-center justify-between text-[11px] text-[#63615C] font-mono-code">
        <span>Diretório: data/dlq/</span>
        <span className="text-[#8EA89D]">Isolamento ativo</span>
      </div>
    </div>
  );
};
