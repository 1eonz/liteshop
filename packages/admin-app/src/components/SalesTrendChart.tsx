import type { JSX } from 'react';
import type { DashboardData } from '@liteshop/shared-types';

interface SalesTrendChartProps {
  points: DashboardData['trend'];
}

/** 看板销售趋势图。结构与 ECharts line option 对齐，使用 SVG 渲染以保持首屏轻量。 */
export function SalesTrendChart({ points }: SalesTrendChartProps): JSX.Element {
  const safePoints = points.length ? points : [{ date: '-', amount: 0 }];
  const max = Math.max(...safePoints.map((point) => point.amount), 1);
  const width = 680;
  const height = 220;
  const left = 24;
  const bottom = 30;
  const usableWidth = width - left * 2;
  const usableHeight = height - bottom - 16;
  const path = safePoints
    .map((point, index) => {
      const x =
        left +
        (safePoints.length === 1
          ? usableWidth / 2
          : (index / (safePoints.length - 1)) * usableWidth);
      const y = 16 + usableHeight - (point.amount / max) * usableHeight;
      return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');
  return (
    <div className="trend-chart" role="img" aria-label="销售额趋势折线图">
      <svg viewBox={`0 0 ${width} ${height}`} preserveAspectRatio="none">
        <line
          className="chart-axis"
          x1={left}
          y1={16 + usableHeight}
          x2={width - left}
          y2={16 + usableHeight}
        />
        <path className="chart-line" d={path} />
        <path
          className="chart-area"
          d={`${path} L ${width - left} ${16 + usableHeight} L ${left} ${16 + usableHeight} Z`}
        />
        {safePoints.map((point, index) => {
          const x =
            left +
            (safePoints.length === 1
              ? usableWidth / 2
              : (index / (safePoints.length - 1)) * usableWidth);
          const y = 16 + usableHeight - (point.amount / max) * usableHeight;
          return (
            <g key={`${point.date}-${index}`}>
              <circle className="chart-dot" cx={x} cy={y} r="4" />
              <text className="chart-label" x={x} y={height - 8} textAnchor="middle">
                {point.date}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
