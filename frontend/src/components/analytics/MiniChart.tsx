/**
 * MiniChart — Lightweight canvas-based chart component.
 * Supports bar, horizontal-bar, and doughnut layouts.
 */
import { useRef, useEffect } from 'react';

interface ChartDataItem {
  label: string;
  value: number;
  color?: string;
}

interface MiniChartProps {
  type: 'bar' | 'horizontal-bar' | 'doughnut';
  data: ChartDataItem[];
  width?: number;
  height?: number;
  title?: string;
}

const DEFAULT_COLORS = [
  '#818cf8', '#34d399', '#fbbf24', '#f472b6', '#60a5fa',
  '#a78bfa', '#2dd4bf', '#fb923c', '#f87171', '#94a3b8',
];

function getColor(index: number, color?: string): string {
  return color || DEFAULT_COLORS[index % DEFAULT_COLORS.length];
}

function drawBar(
  ctx: CanvasRenderingContext2D,
  data: ChartDataItem[],
  w: number,
  h: number,
) {
  const max = Math.max(...data.map((d) => d.value), 1);
  const barWidth = Math.max(8, (w - 40) / data.length - 4);
  const chartH = h - 30;

  ctx.font = '10px Inter, sans-serif';
  ctx.textAlign = 'center';

  data.forEach((d, i) => {
    const barH = (d.value / max) * (chartH - 10);
    const x = 20 + i * (barWidth + 4);
    const y = chartH - barH;
    const color = getColor(i, d.color);

    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(x, y, barWidth, barH, 3);
    ctx.fill();

    ctx.fillStyle = '#94a3b8';
    const label = d.label.length > 6 ? d.label.slice(0, 5) + '…' : d.label;
    ctx.fillText(label, x + barWidth / 2, h - 5);

    ctx.fillStyle = '#e2e8f0';
    ctx.fillText(String(d.value), x + barWidth / 2, y - 4);
  });
}

function drawHorizontalBar(
  ctx: CanvasRenderingContext2D,
  data: ChartDataItem[],
  w: number,
  h: number,
) {
  const max = Math.max(...data.map((d) => d.value), 1);
  const barHeight = Math.min(20, (h - 10) / data.length - 4);
  const labelWidth = 70;

  ctx.font = '10px Inter, sans-serif';
  ctx.textBaseline = 'middle';

  data.forEach((d, i) => {
    const y = 5 + i * (barHeight + 4);
    const barW = ((w - labelWidth - 50) * d.value) / max;
    const color = getColor(i, d.color);

    // Label
    ctx.fillStyle = '#94a3b8';
    ctx.textAlign = 'right';
    const label = d.label.length > 10 ? d.label.slice(0, 9) + '…' : d.label;
    ctx.fillText(label, labelWidth - 4, y + barHeight / 2);

    // Bar
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.roundRect(labelWidth, y, Math.max(barW, 2), barHeight, 3);
    ctx.fill();

    // Value
    ctx.fillStyle = '#e2e8f0';
    ctx.textAlign = 'left';
    ctx.fillText(String(d.value), labelWidth + barW + 6, y + barHeight / 2);
  });
}

function drawDoughnut(
  ctx: CanvasRenderingContext2D,
  data: ChartDataItem[],
  w: number,
  h: number,
) {
  const cx = w / 2;
  const cy = h / 2;
  const radius = Math.min(cx, cy) - 20;
  const inner = radius * 0.55;
  const total = data.reduce((s, d) => s + d.value, 0) || 1;

  let angle = -Math.PI / 2;

  data.forEach((d, i) => {
    const sweep = (d.value / total) * Math.PI * 2;
    const color = getColor(i, d.color);

    ctx.beginPath();
    ctx.arc(cx, cy, radius, angle, angle + sweep);
    ctx.arc(cx, cy, inner, angle + sweep, angle, true);
    ctx.closePath();
    ctx.fillStyle = color;
    ctx.fill();

    angle += sweep;
  });

  // Center label
  ctx.fillStyle = '#e2e8f0';
  ctx.font = 'bold 16px Inter, sans-serif';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';
  ctx.fillText(String(total), cx, cy);
}

export default function MiniChart({ type, data, width = 260, height = 160, title }: MiniChartProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = width * dpr;
    canvas.height = height * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    if (data.length === 0) {
      ctx.fillStyle = '#64748b';
      ctx.font = '12px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.fillText('No data', width / 2, height / 2);
      return;
    }

    if (type === 'bar') drawBar(ctx, data, width, height);
    else if (type === 'horizontal-bar') drawHorizontalBar(ctx, data, width, height);
    else if (type === 'doughnut') drawDoughnut(ctx, data, width, height);
  }, [type, data, width, height, dpr]);

  return (
    <div className="mini-chart">
      {title && <div className="mini-chart__title">{title}</div>}
      <canvas
        ref={canvasRef}
        style={{ width, height }}
        className="mini-chart__canvas"
      />
    </div>
  );
}
