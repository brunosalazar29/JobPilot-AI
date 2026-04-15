"use client";

import { ClipboardList, Loader2, RefreshCw, Send, ShieldCheck } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import type { Application } from "@/types";

const statuses = ["found", "matched", "pending", "running", "prepared", "ready_for_review", "applied", "failed", "rejected", "needs_manual_action"];

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [selected, setSelected] = useState<Application | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) {
      setLoading(true);
    }
    try {
      const data = await apiFetch<Application[]>("/applications");
      setApplications(data);
      setSelected((current) => data.find((item) => item.id === current?.id) ?? data[0] ?? null);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar historial");
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

  async function prepare(applicationId: number) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await apiFetch(`/applications/${applicationId}/prepare`, { method: "POST" });
      setMessage("Preparación encolada");
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo preparar formulario");
    } finally {
      setBusy(false);
    }
  }

  async function updateStatus(applicationId: number, status: string) {
    setBusy(true);
    setError(null);
    try {
      const updated = await apiFetch<Application>(`/applications/${applicationId}/status`, {
        method: "PATCH",
        body: JSON.stringify({ status })
      });
      setApplications((current) => current.map((item) => (item.id === updated.id ? updated : item)));
      setSelected(updated);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo actualizar estado");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader title="Cola" description="Postulaciones, estados, respuestas generadas, logs y errores." />
      <p className="mb-4 text-xs font-medium text-slate-500">
        Actualizacion automatica cada 4 segundos{lastUpdated ? ` - Ultima lectura: ${lastUpdated}` : ""}.
      </p>
      {error ? <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}
      {message ? <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">{message}</p> : null}

      <div className="grid gap-6 xl:grid-cols-[1fr_0.95fr]">
        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="font-semibold text-ink">Historial</h2>
            <button onClick={() => void load(true)} className="inline-flex items-center gap-2 text-sm font-medium text-brand">
              <RefreshCw className="h-4 w-4" />
              Actualizar
            </button>
          </div>

          {loading ? (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando...
            </div>
          ) : applications.length ? (
            <div className="space-y-3">
              {applications.map((application) => (
                <button
                  key={application.id}
                  type="button"
                  onClick={() => setSelected(application)}
                  className="w-full rounded-lg border border-line p-4 text-left hover:border-brand"
                >
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="font-semibold text-ink">{application.position}</p>
                      <p className="mt-1 text-sm text-slate-600">{application.company}</p>
                    </div>
                    <StatusBadge status={application.status} />
                  </div>
                  <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
                    <span>Score: {application.score ? `${application.score}%` : "-"}</span>
                    <span>Docs: {application.document_refs.length}</span>
                    <span>Logs: {application.logs.length}</span>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <EmptyState icon={ClipboardList} title="Sin postulaciones" text="Se crearan automaticamente desde el pipeline cuando existan vacantes compatibles." />
          )}
        </section>

        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          {selected ? (
            <>
              <div className="flex items-start justify-between gap-4">
                <div>
                  <h2 className="font-semibold text-ink">{selected.position}</h2>
                  <p className="mt-1 text-sm text-slate-600">{selected.company}</p>
                </div>
                <StatusBadge status={selected.status} />
              </div>

              <div className="mt-5 flex flex-wrap gap-2">
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void prepare(selected.id)}
                  className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                >
                  {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ShieldCheck className="h-4 w-4" />}
                  Preparar formulario
                </button>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => void updateStatus(selected.id, "applied")}
                  className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm font-semibold text-ink disabled:opacity-60"
                >
                  <Send className="h-4 w-4" />
                  Marcar aplicada
                </button>
                <select
                  value={selected.status}
                  onChange={(event) => void updateStatus(selected.id, event.target.value)}
                  className="rounded-lg border border-line px-3 py-2 text-sm"
                >
                  {statuses.map((status) => (
                    <option key={status} value={status}>
                      {status.replaceAll("_", " ")}
                    </option>
                  ))}
                </select>
              </div>

              <div className="mt-6">
                <h3 className="font-medium text-ink">Respuestas generadas</h3>
                <div className="mt-3 space-y-3">
                  {Object.entries(selected.generated_responses).map(([key, value]) => (
                    <div key={key} className="rounded-lg bg-slate-50 p-3">
                      <p className="text-xs font-semibold uppercase text-slate-500">{key.replaceAll("_", " ")}</p>
                      <p className="mt-2 whitespace-pre-line text-sm leading-6 text-slate-700">{value}</p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-6">
                <h3 className="font-medium text-ink">Logs</h3>
                <div className="mt-3 max-h-64 space-y-2 overflow-auto rounded-lg bg-slate-950 p-3 text-xs text-slate-100">
                  {selected.logs.length ? (
                    selected.logs.map((log, index) => <pre key={index} className="whitespace-pre-wrap">{JSON.stringify(log, null, 2)}</pre>)
                  ) : (
                    <p className="text-slate-300">Sin logs registrados.</p>
                  )}
                </div>
              </div>

              {selected.errors ? <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{selected.errors}</p> : null}
            </>
          ) : (
            <EmptyState icon={ClipboardList} title="Selecciona una aplicación" text="El detalle mostrará respuestas, logs y errores." />
          )}
        </section>
      </div>
    </div>
  );
}
