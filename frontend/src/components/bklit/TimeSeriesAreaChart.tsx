import React, { useState, useMemo } from 'react';
import type { GoldRecord } from '../../types';

interface TimeSeriesAreaChartProps {
  data: GoldRecord[];
  title?: string;
}

export const TimeSeriesAreaChart: React.FC<TimeSeriesAreaChartProps> = ({
  data,
  title = 'Série Temporal Homologada',
}) => {
  const [hoveredPoint, setHoveredPoint] = useState<GoldRecord | null>(null);

  // Statistics
  const stats = useMemo(() => {
    if (!data.length) return { min: 0, max: 0, avg: 0, latest: 0 };
    const values = data.map((d) => d.value);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const avg = values.reduce((a, b) => a + b, 0) / values.length;
    const latest = values[values.length - 1];
    return { min, max, avg, latest };
  }, [data]);

  // Chart dimensions
  const chartDimensions = { width: 800, height: 260, padding: 25 };
  const { width, height, padding } = chartDimensions;

  const chartData = useMemo(() => {
    if (data.length < 2) return [];
    const minVal = stats.min * 0.98;
    const maxVal = stats.max * 1.02;
    const valRange = maxVal - minVal || 1;

    return data.map((d, index) => {
      const x = padding + (index / (data.length - 1)) * (width - padding * 2);
      const y = height - padding - ((d.value - minVal) / valRange) * (height - padding * 2);
      return { ...d, x, y };
    });
  }, [data, stats, width, height, padding]);

  // Generate SVG path for line and area
  const { linePath, areaPath } = useMemo(() => {
    if (!chartData.length) return { linePath: '', areaPath: '' };

    const first = chartData[0];
    const last = chartData[chartData.length - 1];

    let line = `M ${first.x} ${first.y}`;
    for (let i = 1; i < chartData.length; i++) {
      const curr = chartData[i];
      const prev = chartData[i - 1];
      const cx = (prev.x + curr.x) / 2;
      line += ` C ${cx} ${prev.y}, ${cx} ${curr.y}, ${curr.x} ${curr.y}`;
    }

    const area = `${line} L ${last.x} ${height - padding} L ${first.x} ${height - padding} Z`;
    return { linePath: line, areaPath: area };
  }, [chartData, height, padding]);

  if (!data.length) {
    return (
      <div className="dash-card p-8 flex flex-col items-center justify-center min-h-[300px] text-[var(--text-muted)]">
        <p className="text-xs">Aguardando dados da camada Gold para plotagem.</p>
      </div>
    );
  }

  return (
    <div className="dash-card p-6 flex flex-col justify-between relative overflow-hidden">
      {/* Header Info */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <span className="text-[10px] font-mono-code text-[var(--text-muted)] uppercase tracking-wider">
            Camada Gold · Série SGS #11
          </span>
          <h2 className="font-semibold text-sm text-[var(--text-primary)] mt-0.5 tracking-tight">{title}</h2>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono-code">
          <div className="flex flex-col text-right">
            <span className="text-[10px] text-[var(--text-muted)] uppercase">Média</span>
            <span className="text-[var(--text-primary)] font-medium">{stats.avg.toFixed(2)}%</span>
          </div>
          <div className="h-4 w-[1px] bg-[var(--border-app)]" />
          <div className="flex flex-col text-right">
            <span className="text-[10px] text-[var(--text-muted)] uppercase">Min / Max</span>
            <span className="text-[var(--text-secondary)] font-medium">
              {stats.min.toFixed(2)}% — {stats.max.toFixed(2)}%
            </span>
          </div>
        </div>
      </div>

      {/* SVG Chart */}
      <div className="relative w-full aspect-[800/260] min-h-[220px]">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-full overflow-visible"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Linha temporal da série homologada"
        >
          <defs>
            <linearGradient id="dual-chart-gradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="var(--chart-line)" stopOpacity="0.18" />
              <stop offset="100%" stopColor="var(--chart-line)" stopOpacity="0.0" />
            </linearGradient>
          </defs>

          {/* Grid lines */}
          <line x1={padding} y1={padding} x2={width - padding} y2={padding} stroke="var(--border-app)" strokeDasharray="3 3" opacity="0.6" />
          <line x1={padding} y1={height / 2} x2={width - padding} y2={height / 2} stroke="var(--border-app)" strokeDasharray="3 3" opacity="0.6" />
          <line x1={padding} y1={height - padding} x2={width - padding} y2={height - padding} stroke="var(--border-app)" opacity="0.8" />
          <text x={padding - 7} y={padding + 3} textAnchor="end" fill="var(--text-muted)" fontSize="10">{stats.max.toFixed(2)}%</text>
          <text x={padding - 7} y={height / 2 + 3} textAnchor="end" fill="var(--text-muted)" fontSize="10">{stats.avg.toFixed(2)}%</text>
          <text x={padding - 7} y={height - padding + 3} textAnchor="end" fill="var(--text-muted)" fontSize="10">{stats.min.toFixed(2)}%</text>

          {/* Area */}
          <path d={areaPath} fill="url(#dual-chart-gradient)" />

          {/* Stroke Line */}
          <path
            d={linePath}
            fill="none"
            stroke="var(--chart-line)"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          />

          {/* Hover Crosshair & Data points */}
          {chartData.map((pt, i) => (
            <g
              key={i}
              onMouseEnter={() => setHoveredPoint(pt)}
              onMouseLeave={() => setHoveredPoint(null)}
              onClick={() => setHoveredPoint(pt)}
              className="cursor-pointer group"
            >
              <circle
                cx={pt.x}
                cy={pt.y}
                r="3.5"
                className="stroke-[var(--chart-line)] stroke-2 fill-[var(--bg-card)] group-hover:r-5 transition-all"
              />
              <circle cx={pt.x} cy={pt.y} r="14" fill="transparent" />
            </g>
          ))}
        </svg>

        {/* Minimalist Hover Tooltip */}
        {hoveredPoint && (
          <div
            className="absolute z-30 pointer-events-none px-3 py-1.5 rounded-lg bg-[var(--bg-card)] border border-[var(--border-hover)] shadow-xl text-xs transition-all transform -translate-x-1/2"
            style={{
              left: `${((hoveredPoint as any).x / width) * 100}%`,
              top: `${Math.max(8, ((hoveredPoint as any).y / height) * 100 - 18)}%`,
            }}
          >
            <div className="text-[10px] text-[var(--text-muted)] font-mono-code">{hoveredPoint.date}</div>
            <div className="text-[var(--text-primary)] font-bold text-xs">
              {hoveredPoint.value.toFixed(2)}% <span className="text-[10px] text-[var(--text-muted)] font-normal font-mono-code">a.a.</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer labels */}
      <div className="flex justify-between items-center text-[11px] text-[var(--text-muted)] mt-2 pt-3 border-t border-[var(--border-app)] font-mono-code">
        <span>Início: {data[0]?.date}</span>
        <span className="text-[var(--text-secondary)]">{data.length} amostras homologadas</span>
        <span>Recente: {data[data.length - 1]?.date}</span>
      </div>
    </div>
  );
};
