import React from 'react';
import { CheckCircle2, AlertTriangle } from 'lucide-react';

interface HealthGaugeProps {
  score: number;
  totalRuns: number;
  quarantinedRuns: number;
}

export const HealthGauge: React.FC<HealthGaugeProps> = ({
  score,
  totalRuns,
  quarantinedRuns,
}) => {
  const isHealthy = score >= 90;

  // Geometry
  const radius = 64;
  const strokeWidth = 7;
  const circumference = 2 * Math.PI * radius;
  const arcLength = circumference * (240 / 360);
  const strokeDashoffset = arcLength - (arcLength * Math.min(100, Math.max(0, score))) / 100;

  const colorClass = isHealthy
    ? 'stroke-[#8EA89D]'
    : 'stroke-[#C87D6E]';

  return (
    <div className="editorial-card p-6 flex flex-col items-center justify-between h-full">
      <div className="w-full flex items-center justify-between">
        <span className="text-[10px] font-mono-code text-[#9E9C96] uppercase tracking-wider">
          Saúde operacional
        </span>
        <span className="text-[10px] text-[#63615C] font-mono-code">
          {totalRuns} runs analisadas
        </span>
      </div>

      {/* SVG Arc Gauge */}
      <div className="relative flex items-center justify-center my-3">
        <svg width="170" height="170" viewBox="0 0 170 170" className="transform -rotate-[210deg]">
          {/* Background track */}
          <circle
            cx="85"
            cy="85"
            r={radius}
            fill="transparent"
            stroke="rgba(255, 255, 255, 0.04)"
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeLinecap="round"
          />
          {/* Active progress arc */}
          <circle
            cx="85"
            cy="85"
            r={radius}
            fill="transparent"
            className={`${colorClass} transition-all duration-700 ease-out`}
            strokeWidth={strokeWidth}
            strokeDasharray={`${arcLength} ${circumference}`}
            strokeDashoffset={strokeDashoffset}
            strokeLinecap="round"
          />
        </svg>

        {/* Center Score */}
        <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
          <div className="text-3xl font-bold tracking-tight font-data text-[#F3F2EE]">
            {score.toFixed(0)}
            <span className="text-base text-[#9E9C96] font-normal">%</span>
          </div>
          <span className="text-[10px] uppercase tracking-wider text-[#63615C] font-mono-code mt-0.5">
            Integridade
          </span>
        </div>
      </div>

      {/* Diagnostic Message */}
      <div className="w-full text-center border-t border-white/[0.04] pt-3">
        <div className="flex items-center justify-center gap-1.5 text-xs font-medium mb-0.5">
          {isHealthy ? (
            <>
              <CheckCircle2 className="w-3.5 h-3.5 text-[#8EA89D] stroke-[1.75]" />
              <span className="text-[#F3F2EE] text-xs">Contratos 100% Homologados</span>
            </>
          ) : (
            <>
              <AlertTriangle className="w-3.5 h-3.5 text-[#C87D6E] stroke-[1.75]" />
              <span className="text-[#C87D6E] text-xs">{quarantinedRuns} Carga(s) Isolada(s)</span>
            </>
          )}
        </div>
        <p className="text-[11px] text-[#63615C] leading-relaxed">
          {totalRuns === 0
            ? 'Aguardando execuções para aferir integridade.'
            : isHealthy
              ? 'Todos os lotes atenderam às regras sem anomalias.'
              : 'Circuit Breaker impediu poluição da camada Gold.'}
        </p>
      </div>
    </div>
  );
};
