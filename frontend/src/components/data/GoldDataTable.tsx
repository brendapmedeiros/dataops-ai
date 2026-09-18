import React, { useState } from 'react';
import type { GoldRecord } from '../../types';
import { Search } from 'lucide-react';

interface GoldDataTableProps {
  data: GoldRecord[];
}

export const GoldDataTable: React.FC<GoldDataTableProps> = ({ data }) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filtered = data.filter(
    (d) =>
      d.date.includes(searchTerm) ||
      d.value.toString().includes(searchTerm) ||
      d.source.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="editorial-card p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
        <div>
          <span className="text-[10px] font-mono-code text-[#9E9C96] uppercase tracking-wider">
            Camada Gold • bcb_timeseries
          </span>
          <h3 className="font-display font-semibold text-sm text-[#F3F2EE] mt-0.5 tracking-tight">
            Registros Homologados no Banco Analítico
          </h3>
        </div>

        {/* Search */}
        <div className="relative w-full sm:w-56">
          <Search className="w-3.5 h-3.5 text-[#63615C] absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Buscar por data ou valor..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-8 pr-3 py-1.5 rounded-lg bg-[#16181D]/80 border border-white/[0.06] text-xs text-[#F3F2EE] placeholder-[#63615C] focus:outline-none focus:border-white/[0.15] transition-colors font-sans"
          />
        </div>
      </div>

      {/* Table */}
      <div className="w-full overflow-x-auto rounded-lg border border-white/[0.04]">
        <table className="w-full text-left text-xs">
          <thead className="bg-[#16181D]/40 text-[#9E9C96] uppercase font-mono-code text-[10px] tracking-wider border-b border-white/[0.04]">
            <tr>
              <th className="py-2.5 px-4 font-normal">Data</th>
              <th className="py-2.5 px-4 font-normal">Taxa Selic (%)</th>
              <th className="py-2.5 px-4 font-normal">Série</th>
              <th className="py-2.5 px-4 font-normal">Origem</th>
              <th className="py-2.5 px-4 font-normal text-right">Integridade</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.04] text-[#F3F2EE]/90 font-mono-code">
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={5} className="py-8 text-center text-[#63615C] font-sans">
                  Nenhum registro encontrado.
                </td>
              </tr>
            ) : (
              filtered.map((row, idx) => (
                <tr key={idx} className="hover:bg-white/[0.02] transition-colors">
                  <td className="py-2.5 px-4 font-medium text-[#F3F2EE]">{row.date}</td>
                  <td className="py-2.5 px-4 text-[#8EA89D] font-data font-semibold">{row.value.toFixed(2)}%</td>
                  <td className="py-2.5 px-4 text-[#63615C]">#{row.series_code}</td>
                  <td className="py-2.5 px-4 text-[#9E9C96] font-sans">{row.source}</td>
                  <td className="py-2.5 px-4 text-right">
                    <span className="text-[10px] text-[#8EA89D] font-mono-code">
                      ● Aprovado
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center justify-between mt-3 text-[11px] text-[#63615C] font-mono-code">
        <span>Total: {filtered.length} registros</span>
        <span>Persistência: PostgreSQL / SQLite</span>
      </div>
    </div>
  );
};
