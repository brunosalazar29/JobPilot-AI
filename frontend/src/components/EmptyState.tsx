import type { LucideIcon } from "lucide-react";

export function EmptyState({
  icon: Icon,
  title,
  text
}: {
  icon: LucideIcon;
  title: string;
  text: string;
}) {
  return (
    <div className="rounded-lg border border-dashed border-line bg-white p-8 text-center">
      <Icon aria-hidden className="mx-auto h-8 w-8 text-slate-400" />
      <h2 className="mt-3 text-base font-semibold text-ink">{title}</h2>
      <p className="mx-auto mt-2 max-w-md text-sm text-slate-500">{text}</p>
    </div>
  );
}
