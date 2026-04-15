"use client";

import { Activity, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import type { TaskRun } from "@/types";

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskRun[]>([]);
  const [selected, setSelected] = useState<TaskRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) {
      setLoading(true);
    }
    try {
      const data = await apiFetch<TaskRun[]>("/tasks");
      setTasks(data);
      setSelected((current) => data.find((task) => task.id === current?.id) ?? data[0] ?? null);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar tareas");
    } finally {
      if (showSpinner) {
        setLoading(false);
      }
    }
  }, []);

  useEffect(() => {
    void load(true);
    const intervalId = window.setInterval(() => {
      void load(false);
    }, 4000);
    return () => window.clearInterval(intervalId);
  }, [load]);

  return (
    <div>
      <PageHeader
        title="Tareas"
        description="Estado de jobs Celery, timestamps, logs y errores."
        action={
          <button onClick={() => void load(true)} className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white">
            <RefreshCw className="h-4 w-4" />
            Actualizar
          </button>
        }
      />
      <p className="mb-4 text-xs font-medium text-slate-500">
        Actualizacion automatica cada 4 segundos{lastUpdated ? ` - Ultima lectura: ${lastUpdated}` : ""}.
      </p>

      {error ? <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}

      <div className="grid gap-6 xl:grid-cols-[1fr_0.9fr]">
        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando tareas...
            </div>
          ) : tasks.length ? (
            <div className="space-y-3">
              {tasks.map((task) => (
                <button
                  key={task.id}
                  type="button"
                  onClick={() => setSelected(task)}
                  className="w-full rounded-lg border border-line p-4 text-left hover:border-brand"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-ink">{task.task_name}</p>
                      <p className="mt-1 text-xs text-slate-500">{new Date(task.created_at).toLocaleString()}</p>
                    </div>
                    <StatusBadge status={task.status} />
                  </div>
                  <div className="mt-3 h-2 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-brand" style={{ width: `${task.progress}%` }} />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState icon={Activity} title="Sin tareas" text="Las búsquedas, parseos y automatizaciones aparecerán aquí." />
          )}
        </section>

        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          {selected ? (
            <>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-ink">{selected.task_name}</h2>
                  <p className="mt-1 text-sm text-slate-600">Task run #{selected.id}</p>
                </div>
                <StatusBadge status={selected.status} />
              </div>
              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <Info label="Celery ID" value={selected.celery_task_id ?? "-"} />
                <Info label="Progreso" value={`${selected.progress}%`} />
                <Info label="Inicio" value={selected.started_at ? new Date(selected.started_at).toLocaleString() : "-"} />
                <Info label="Fin" value={selected.completed_at ? new Date(selected.completed_at).toLocaleString() : "-"} />
              </dl>
              {selected.error_message ? (
                <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{selected.error_message}</p>
              ) : null}
              <h3 className="mt-6 font-medium text-ink">Payload</h3>
              <pre className="mt-2 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(selected.payload, null, 2)}</pre>
              <h3 className="mt-6 font-medium text-ink">Resultado</h3>
              <pre className="mt-2 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(selected.result, null, 2)}</pre>
              <h3 className="mt-6 font-medium text-ink">Logs</h3>
              <pre className="mt-2 max-h-64 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">{JSON.stringify(selected.logs, null, 2)}</pre>
            </>
          ) : (
            <EmptyState icon={Activity} title="Selecciona una tarea" text="Revisa detalle técnico, errores y logs." />
          )}
        </section>
      </div>
    </div>
  );
}

function Info({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg bg-slate-50 p-3">
      <dt className="text-xs font-semibold uppercase text-slate-500">{label}</dt>
      <dd className="mt-1 break-words text-slate-700">{value}</dd>
    </div>
  );
}
