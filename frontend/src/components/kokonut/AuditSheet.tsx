import React, { useState } from 'react';
import type { HistoryRecord } from '../../types';
import { Copy, Check, Lock, X } from 'lucide-react';

interface AuditSheetProps {
  record: HistoryRecord | null;
  isOpen: boolean;
  onClose: () => void;
}

export const AuditSheet: React.FC<AuditSheetProps> = ({ record, isOpen, onClose }) => {
  const [copied, setCopied] = useState(false);

  if (!isOpen || !record) return null;

  const hash = record.audit_hash || 'SHA-256-PENDING-HOMOLOGATION';

  const handleCopy = () => {
    navigator.clipboard.writeText(hash);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-150">
      <div className="relative w-full max-w-lg bg-[#111317] border border-white/[0.08] rounded-xl p-6 shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5">
            <Lock className="w-4 h-4 text-[#C5A880]" />
            <h3 className="font-display font-semibold text-sm text-[#F3F2EE]">Selo de Auditoria Criptográfica</h3>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-md text-[#9E9C96] hover:text-[#F3F2EE] transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content */}
        <div className="py-4 space-y-4">
          <div>
            <label className="text-[10px] text-[#9E9C96] font-mono-code block mb-1.5 uppercase">
              Assinatura Imutável SHA-256
            </label>
            <div className="flex items-center gap-2 p-3 rounded-lg bg-[#0B0C0E] border border-white/[0.06] font-mono-code text-xs text-[#8EA89D] break-all select-all">
              <span>{hash}</span>
              <button
                onClick={handleCopy}
                className="ml-auto p-1 rounded hover:bg-white/10 text-[#9E9C96] hover:text-[#F3F2EE] transition-colors shrink-0"
                title="Copiar Hash"
              >
                {copied ? <Check className="w-3.5 h-3.5 text-[#8EA89D]" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Details Grid */}
          <div className="grid grid-cols-2 gap-2 text-xs font-mono-code">
            <div className="p-3 rounded-lg bg-[#16181D]/60 border border-white/[0.04]">
              <div className="text-[#63615C] text-[10px] uppercase">Run ID</div>
              <div className="text-[#F3F2EE] mt-0.5">#{record.run_id.slice(0, 10)}</div>
            </div>
            <div className="p-3 rounded-lg bg-[#16181D]/60 border border-white/[0.04]">
              <div className="text-[#63615C] text-[10px] uppercase">Cenário</div>
              <div className="text-[#F3F2EE] mt-0.5 capitalize font-sans text-xs">{record.scenario.replace('_', ' ')}</div>
            </div>
            <div className="p-3 rounded-lg bg-[#16181D]/60 border border-white/[0.04]">
              <div className="text-[#63615C] text-[10px] uppercase">Amostras Verificadas</div>
              <div className="text-[#F3F2EE] mt-0.5 font-data font-semibold">{record.rows_checked ?? 22}</div>
            </div>
            <div className="p-3 rounded-lg bg-[#16181D]/60 border border-white/[0.04]">
              <div className="text-[#63615C] text-[10px] uppercase">Ação do Circuit Breaker</div>
              <div className={`mt-0.5 font-sans font-medium text-xs ${record.quarantined ? 'text-[#C87D6E]' : 'text-[#8EA89D]'}`}>
                {record.quarantined ? 'Isolado em DLQ' : 'Homologado na Gold'}
              </div>
            </div>
          </div>

          <p className="text-[11px] text-[#9E9C96] leading-relaxed font-sans pt-1">
            Esta assinatura sela determinística e matematicamente os dados e o consenso multiagente, assegurando conformidade de dados e não-repúdio.
          </p>
        </div>

        {/* Footer */}
        <div className="pt-3 border-t border-white/[0.06] flex justify-end">
          <button
            onClick={onClose}
            className="px-3.5 py-1.5 rounded-lg text-xs font-medium bg-[#16181D] hover:bg-[#1D2027] text-[#F3F2EE] border border-white/[0.06] transition-colors"
          >
            Fechar
          </button>
        </div>
      </div>
    </div>
  );
};
