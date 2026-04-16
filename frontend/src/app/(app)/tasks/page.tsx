"use client";

import { Activity, Loader2, RefreshCw, TerminalSquare } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import {
  buildConsoleEntries,
  formatDateTime,
  formatDuration,
  formatRelativeTime,
  getTaskCurrentMessage,
  getTaskDescription,
  getTaskLabel,
  translateLogMessage
} from "@/lib/userText";
import type { Application, TaskRun } from "@/types";

export default function TasksPage() {
  const [tasks, setTasks] = useState<TaskRun[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [selected, setSelected] = useState<TaskRun | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) {
      setLoading(true);
    }
    setError(null);
    try {
      const [taskData, applicationData] = await Promise.all([
        apiFetch<TaskRun[]>("/tasks"),
        apiFetch<Application[]>("/applications")
      ]);
      setTasks(taskData);
      setApplications(applicationData);
      setSelected((current) => taskData.find((task) => task.id === current?.id) ?? taskData[0] ?? null);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar la actividad");
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

  const consoleEntries = useMemo(() => buildConsoleEntries(tasks, applications), [tasks, applications]);

  return (
    <div>
      <PageHeader
        title="Actividad del sistema"
        description="Muestra qué proceso corrió, cuánto tardó y qué hizo el sistema paso a paso."
        action={
          <button
            onClick={() => void load(true)}
            className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm font-semibold text-ink"
          >
            <RefreshCw className="h-4 w-4" />
            Actualizar ahora
          </button>
        }
      />

      <p className="mb-4 text-xs font-medium text-slate-500">
        Actualización automática cada 4 segundos
        {lastUpdated ? ` · Última actualización ${formatRelativeTime(lastUpdated)} (${formatDateTime(lastUpdated)})` : ""}
      </p>

      {error ? <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          {loading ? (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando procesos...
            </div>
          ) : tasks.length ? (
            <div className="space-y-3">
              {tasks.map((task) => (
                <button
                  key={task.id}
                  type="button"
                  onClick={() => setSelected(task)}
                  className="w-full rounded-lg border border-line p-4 text-left transition hover:border-brand"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-ink">{getTaskLabel(task.task_name)}</p>
                      <p className="mt-1 text-sm text-slate-600">{getTaskCurrentMessage(task)}</p>
                    </div>
                    <StatusBadge status={task.status} />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                    <span>Creado {formatRelativeTime(task.created_at)}</span>
                    <span>Duración {formatDuration(task.started_at, task.completed_at)}</span>
                    <span>Progreso {task.progress}%</span>
                  </div>
                  <div className="mt-3 h-2 rounded-full bg-slate-100">
                    <div className="h-2 rounded-full bg-brand" style={{ width: `${task.progress}%` }} />
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState icon={Activity} title="Sin procesos" text="Las búsquedas, análisis y automatizaciones aparecerán aquí." />
          )}
        </section>

        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          {selected ? (
            <>
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h2 className="font-semibold text-ink">{getTaskLabel(selected.task_name)}</h2>
                  <p className="mt-1 text-sm text-slate-600">{getTaskDescription(selected.task_name)}</p>
                </div>
                <StatusBadge status={selected.status} />
              </div>

              <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <Info label="Inicio" value={selected.started_at ? formatDateTime(selected.started_at) : "-"} />
                <Info label="Fin" value={selected.completed_at ? formatDateTime(selected.completed_at) : "-"} />
                <Info label="Tiempo total" value={formatDuration(selected.started_at, selected.completed_at)} />
                <Info label="Progreso" value={`${selected.progress}%`} />
              </dl>

              {selected.error_message ? (
                <p className="mt-5 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{selected.error_message}</p>
              ) : null}

              <div className="mt-6 rounded-lg border border-line bg-slate-950 p-4 text-slate-100">
                <div className="flex items-center gap-2">
                  <TerminalSquare className="h-4 w-4 text-emerald-300" />
                  <h3 className="font-medium">Consola del proceso</h3>
                </div>
                <div className="mt-3 max-h-72 space-y-3 overflow-auto">
                  {selected.logs.length ? (
                    [...selected.logs].reverse().map((log, index) => (
                      <div key={index} className="border-b border-slate-800 pb-3 text-sm last:border-b-0 last:pb-0">
                        <p>{typeof log.message === "string" ? translateLogMessage(log.message) ?? log.message : "Evento registrado"}</p>
                        {typeof log.timestamp === "string" ? (
                          <p className="mt-1 text-xs text-slate-400">
                            {formatDateTime(log.timestamp)} · {formatRelativeTime(log.timestamp)}
                          </p>
                        ) : null}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-slate-400">Este proceso todavía no tiene eventos visibles.</p>
                  )}
                </div>
              </div>
            </>
          ) : (
            <EmptyState icon={Activity} title="Selecciona un proceso" text="El detalle mostrará tiempo, estado y eventos del proceso." />
          )}
        </section>
      </div>

      <section className="mt-6 rounded-lg border border-line bg-slate-950 p-5 text-slate-100 shadow-panel">
        <div className="flex items-center gap-2">
          <TerminalSquare className="h-5 w-5 text-emerald-300" />
          <h2 className="font-semibold">Consola general</h2>
        </div>
        <p className="mt-2 text-sm text-slate-400">Últimos eventos combinados de la cola y de los procesos.</p>
        <div className="mt-4 max-h-[360px] space-y-3 overflow-auto rounded-lg border border-slate-800 bg-slate-950/80 p-3">
          {consoleEntries.length ? (
            consoleEntries.map((entry) => (
              <div key={entry.key} className="border-b border-slate-800 pb-3 last:border-b-0 last:pb-0">
                <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                  <span>{formatDateTime(entry.timestamp)}</span>
                  <span>·</span>
                  <span>{entry.title}</span>
                </div>
                <p className="mt-1 text-sm text-slate-100">{entry.detail}</p>
              </div>
            ))
          ) : (
            <p className="text-sm text-slate-400">Todavía no hay actividad registrada.</p>
          )}
        </div>
      </section>
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
