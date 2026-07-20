/**
 * Common reusable UI components.
 */

export function LoadingSpinner({ message = 'Loading...' }: { message?: string }) {
  return (
    <div className="loading-spinner">
      <div className="loading-spinner__ring" />
      <span className="loading-spinner__text">{message}</span>
    </div>
  );
}

export function ErrorBanner({
  message,
  onDismiss,
}: {
  message: string;
  onDismiss?: () => void;
}) {
  return (
    <div className="error-banner">
      <span className="error-banner__icon">⚠</span>
      <span className="error-banner__text">{message}</span>
      {onDismiss && (
        <button className="error-banner__close" onClick={onDismiss}>
          ✕
        </button>
      )}
    </div>
  );
}

export function Badge({
  label,
  color = '#818cf8',
  small = false,
}: {
  label: string;
  color?: string;
  small?: boolean;
}) {
  return (
    <span
      className={`badge ${small ? 'badge--small' : ''}`}
      style={{ borderColor: color, color }}
    >
      {label}
    </span>
  );
}

export function StatCard({
  title,
  value,
  subtitle,
  color = '#818cf8',
}: {
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
}) {
  return (
    <div className="stat-card" style={{ borderTopColor: color }}>
      <div className="stat-card__value" style={{ color }}>
        {typeof value === 'number' ? value.toLocaleString() : value}
      </div>
      <div className="stat-card__title">{title}</div>
      {subtitle && <div className="stat-card__subtitle">{subtitle}</div>}
    </div>
  );
}
