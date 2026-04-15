import type { LucideIcon } from "lucide-react";

export function MetricCard({
  label,
  value,
  helper,
  icon: Icon
}: {
  label: string;
  value: string | number;
  helper?: string;
  icon: LucideIcon;
}) {
  return (
    <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-slate-500">{label}</p>
          <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
        </div>
        <div className="rounded-lg bg-teal-50 p-2 text-brand">
          <Icon aria-hidden className="h-5 w-5" />
        </div>
      </div>
      {helper ? <p className="mt-4 text-sm text-slate-500">{helper}</p> : null}
    </div>
  );
}
