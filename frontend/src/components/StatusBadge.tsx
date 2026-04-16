import clsx from "clsx";
import { getStatusLabel } from "@/lib/userText";

const statusStyles: Record<string, string> = {
  pending: "bg-amber-100 text-amber-800 border-amber-200",
  found: "bg-slate-100 text-slate-700 border-slate-200",
  matched: "bg-cyan-100 text-cyan-800 border-cyan-200",
  queued: "bg-amber-100 text-amber-800 border-amber-200",
  preparing: "bg-sky-100 text-sky-800 border-sky-200",
  applying: "bg-indigo-100 text-indigo-800 border-indigo-200",
  running: "bg-sky-100 text-sky-800 border-sky-200",
  prepared: "bg-teal-100 text-teal-800 border-teal-200",
  completed: "bg-emerald-100 text-emerald-800 border-emerald-200",
  parsed: "bg-emerald-100 text-emerald-800 border-emerald-200",
  uploaded: "bg-slate-100 text-slate-700 border-slate-200",
  ready_for_review: "bg-teal-100 text-teal-800 border-teal-200",
  applied: "bg-indigo-100 text-indigo-800 border-indigo-200",
  failed: "bg-rose-100 text-rose-800 border-rose-200",
  rejected: "bg-rose-100 text-rose-800 border-rose-200",
  needs_manual_action: "bg-orange-100 text-orange-800 border-orange-200",
  paused: "bg-slate-200 text-slate-800 border-slate-300",
  cancelled: "bg-rose-50 text-rose-700 border-rose-200"
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span
      className={clsx(
        "inline-flex items-center rounded-full border px-2.5 py-1 text-xs font-semibold",
        statusStyles[status] ?? "bg-slate-100 text-slate-700 border-slate-200"
      )}
    >
      {getStatusLabel(status)}
    </span>
  );
}
