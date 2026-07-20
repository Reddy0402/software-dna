/**
 * HealthScoreCard — Circular score gauge with grade and sub-metric bars.
 */
import { useRef, useEffect } from 'react';
import type { HealthReport } from '../../types/analytics';

interface HealthScoreCardProps {
  report: HealthReport;
}

function ScoreGauge({ score, grade }: { score: number; grade: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
  const size = 180;

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, size, size);

    const cx = size / 2;
    const cy = size / 2;
    const radius = 72;
    const lineWidth = 10;

    // Background ring
    ctx.beginPath();
    ctx.arc(cx, cy, radius, 0, Math.PI * 2);
    ctx.strokeStyle = 'rgba(148, 163, 184, 0.15)';
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Score ring
    const pct = Math.min(score / 100, 1);
    const startAngle = -Math.PI / 2;
    const endAngle = startAngle + pct * Math.PI * 2;

    const gradient = ctx.createConicGradient(startAngle, cx, cy);
    if (score >= 80) {
      gradient.addColorStop(0, '#34d399');
      gradient.addColorStop(1, '#2dd4bf');
    } else if (score >= 60) {
      gradient.addColorStop(0, '#fbbf24');
      gradient.addColorStop(1, '#fb923c');
    } else {
      gradient.addColorStop(0, '#f87171');
      gradient.addColorStop(1, '#f472b6');
    }

    ctx.beginPath();
    ctx.arc(cx, cy, radius, startAngle, endAngle);
    ctx.strokeStyle = gradient;
    ctx.lineWidth = lineWidth;
    ctx.lineCap = 'round';
    ctx.stroke();

    // Score text
    ctx.fillStyle = '#e2e8f0';
    ctx.font = 'bold 36px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(String(Math.round(score)), cx, cy - 6);

    // Grade
    const gradeColor =
      grade === 'A' ? '#34d399' :
      grade === 'B' ? '#2dd4bf' :
      grade === 'C' ? '#fbbf24' :
      grade === 'D' ? '#fb923c' : '#f87171';
    ctx.fillStyle = gradeColor;
    ctx.font = 'bold 18px Inter, sans-serif';
    ctx.fillText(`Grade ${grade}`, cx, cy + 26);
  }, [score, grade, dpr]);

  return (
    <canvas
      ref={canvasRef}
      style={{ width: size, height: size }}
      className="score-gauge__canvas"
    />
  );
}

function SubScoreBar({ name, score }: { name: string; score: number }) {
  const displayName = name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());

  const color =
    score >= 80 ? 'var(--accent-emerald)' :
    score >= 60 ? 'var(--accent-amber)' :
    'var(--accent-red)';

  return (
    <div className="sub-score">
      <div className="sub-score__header">
        <span className="sub-score__name">{displayName}</span>
        <span className="sub-score__value" style={{ color }}>{Math.round(score)}</span>
      </div>
      <div className="sub-score__track">
        <div
          className="sub-score__fill"
          style={{ width: `${Math.min(score, 100)}%`, backgroundColor: color }}
        />
      </div>
    </div>
  );
}

export default function HealthScoreCard({ report }: HealthScoreCardProps) {
  const subScores = report.sub_scores || {};
  const structCounts = report.structural_counts as Record<string, number> || {};

  return (
    <div className="health-card">
      <div className="health-card__gauge-section">
        <ScoreGauge score={report.overall_score} grade={report.grade} />
        <div className="health-card__summary">
          <div className="health-card__stat">
            <span className="health-card__stat-value">{structCounts.total_files ?? 0}</span>
            <span className="health-card__stat-label">Files</span>
          </div>
          <div className="health-card__stat">
            <span className="health-card__stat-value">{structCounts.total_entities ?? 0}</span>
            <span className="health-card__stat-label">Entities</span>
          </div>
          <div className="health-card__stat">
            <span className="health-card__stat-value">{structCounts.total_dependencies ?? 0}</span>
            <span className="health-card__stat-label">Dependencies</span>
          </div>
        </div>
      </div>

      <div className="health-card__scores">
        <h3 className="health-card__scores-title">Sub-Scores</h3>
        {Object.entries(subScores).map(([name, score]) => (
          <SubScoreBar key={name} name={name} score={score} />
        ))}
      </div>

      <div className="health-card__details">
        <h3 className="health-card__details-title">Key Metrics</h3>
        <div className="health-card__metrics-grid">
          {report.size_metrics && (
            <>
              <div className="health-card__metric">
                <span className="health-card__metric-label">Avg Method Size</span>
                <span className="health-card__metric-value">
                  {(report.size_metrics as Record<string, number>).avg_method_size ?? 0} lines
                </span>
              </div>
              <div className="health-card__metric">
                <span className="health-card__metric-label">Avg Class Size</span>
                <span className="health-card__metric-value">
                  {(report.size_metrics as Record<string, number>).avg_class_size ?? 0} lines
                </span>
              </div>
            </>
          )}
          {report.graph_density && (
            <>
              <div className="health-card__metric">
                <span className="health-card__metric-label">Graph Density</span>
                <span className="health-card__metric-value">
                  {(report.graph_density as Record<string, number>).density ?? 0}
                </span>
              </div>
              <div className="health-card__metric">
                <span className="health-card__metric-label">Connectivity</span>
                <span className="health-card__metric-value">
                  {((report.graph_density as Record<string, number>).connectivity_ratio * 100 ?? 0).toFixed(0)}%
                </span>
              </div>
            </>
          )}
          {report.coupling && (
            <div className="health-card__metric">
              <span className="health-card__metric-label">Avg Instability</span>
              <span className="health-card__metric-value">
                {(report.coupling as Record<string, number>).avg_instability ?? 0}
              </span>
            </div>
          )}
          {report.cycle_info && (
            <div className="health-card__metric">
              <span className="health-card__metric-label">Dependency Cycles</span>
              <span className="health-card__metric-value">
                {(report.cycle_info as Record<string, number>).total_cycles ?? 0}
              </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
