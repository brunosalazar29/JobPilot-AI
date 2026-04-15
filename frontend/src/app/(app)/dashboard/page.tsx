"use client";

import { AlertCircle, CheckCircle2, FilePlus2, Loader2, RefreshCw } from "lucide-react";
import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import type { Application, DetectedProfile, Resume, TaskRun } from "@/types";

type QueueCounts = {
  applied: number;
  ready_for_review: number;
  failed: number;
  needs_manual_action: number;
};

export default function DashboardPage() {
  const [detected, setDetected] = useState<DetectedProfile | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [tasks, setTasks] = useState<TaskRun[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) {
      setLoading(true);
    }
    setError(null);
    try {
      const [profileData, resumeData, applicationData, taskData] = await Promise.all([
        apiFetch<DetectedProfile>("/profile/detected"),
        apiFetch<Resume[]>("/documents"),
        apiFetch<Application[]>("/applications"),
        apiFetch<TaskRun[]>("/tasks")
      ]);
      setDetected(profileData);
      setResumes(resumeData);
      setApplications(applicationData);
      setTasks(taskData);
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el panel");
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

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Selecciona un CV en PDF o DOCX");
      return;
    }
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await apiFetch<Resume>("/documents/upload", { method: "POST", body: formData });
      setFile(null);
      setMessage("CV recibido. JobPilot inicio analisis, perfil, busqueda configurada, matching y cola.");
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo subir el CV");
    } finally {
      setBusy(false);
    }
  }

  const queueCounts = useMemo<QueueCounts>(() => {
    return applications.reduce(
      (counts, application) => {
        if (application.status in counts) {
          counts[application.status as keyof QueueCounts] += 1;
        }
        return counts;
      },
      { applied: 0, ready_for_review: 0, failed: 0, needs_manual_action: 0 }
    );
  }, [applications]);

  const latestResume = resumes[0];
  const runningTasks = tasks.filter((task) => ["queued", "running"].includes(task.status)).slice(0, 3);
  const visibleApplications = applications.slice(0, 8);
  const hasParsedCv = resumes.some((resume) => resume.status === "parsed");

  return (
    <div>
      <PageHeader
        title="Panel"
        description="Sube tu CV y monitorea lo que JobPilot hace en segundo plano."
        action={
          <button onClick={() => void load(true)} className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm font-semibold text-ink">
            <RefreshCw className="h-4 w-4" />
            Actualizar
          </button>
        }
      />
      <p className="mb-4 text-xs font-medium text-slate-500">
        Actualizacion automatica cada 4 segundos{lastUpdated ? ` - Ultima lectura: ${lastUpdated}` : ""}.
      </p>

      {error ? <Notice tone="error" text={error} /> : null}
      {message ? <Notice tone="success" text={message} /> : null}

      <form onSubmit={upload} className="rounded-lg border border-line bg-white p-5 shadow-panel">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end">
          <label className="flex-1 text-sm font-medium text-slate-700">
            CV principal
            <input
              type="file"
              accept=".pdf,.docx"
              onChange={selectFile}
              className="mt-2 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm"
            />
          </label>
          <button
            type="submit"
            disabled={busy}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
          >
            {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FilePlus2 className="h-4 w-4" />}
            Subir e iniciar
          </button>
        </div>
        <p className="mt-3 text-sm text-slate-500">
          Al subirlo se ejecuta: parse_cv, infer_profile, collect_jobs, match_jobs y create_queue_items.
        </p>
      </form>

      {loading ? (
        <div className="mt-6 flex items-center gap-2 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando estado...
        </div>
      ) : (
        <>
          <section className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
              <h2 className="font-semibold text-ink">CV y perfil detectado</h2>
              <div className="mt-4 space-y-4">
                <InfoRow label="CV" value={latestResume?.original_filename ?? "Sin CV cargado"} status={latestResume?.status} />
                <InfoRow label="Completitud" value={detected ? `${detected.completeness}%` : "-"} />
                <InfoRow label="Nombre" value={detected?.profile.full_name ?? "No detectado"} />
                <InfoRow label="Roles probables" value={detected?.profile.target_roles?.join(", ") || "No inferidos"} />
                <InfoRow label="Skills" value={detected?.profile.skills?.slice(0, 8).join(", ") || "No detectadas"} />
              </div>
            </div>

            <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
              <h2 className="font-semibold text-ink">Faltantes utiles</h2>
              <p className="mt-2 text-sm text-slate-600">No bloquean el flujo; solo mejoran matching o formularios.</p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                {detected?.recommendations.length ? (
                  detected.recommendations.map((item) => (
                    <div key={item.field} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
                      <p className="font-semibold text-amber-900">{item.message}</p>
                      <p className="mt-1 text-amber-800">{item.reason}</p>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                    <CheckCircle2 className="h-4 w-4" />
                    El CV tiene datos suficientes para iniciar.
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
            <Counter label="Enviadas" value={queueCounts.applied} />
            <Counter label="Listas para revisar" value={queueCounts.ready_for_review} />
            <Counter label="Fallidas" value={queueCounts.failed} />
            <Counter label="Accion manual" value={queueCounts.needs_manual_action} />
          </section>

          <section className="mt-6 rounded-lg border border-line bg-white p-5 shadow-panel">
            <div className="mb-4 flex items-center justify-between gap-3">
              <h2 className="font-semibold text-ink">Cola de postulaciones</h2>
              <StatusBadge status={runningTasks.length ? "running" : "completed"} />
            </div>
            {visibleApplications.length ? (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="text-xs uppercase text-slate-500">
                    <tr>
                      <th className="py-2">Estado</th>
                      <th className="py-2">Puesto</th>
                      <th className="py-2">Empresa</th>
                      <th className="py-2">Score</th>
                      <th className="py-2">Motivo / link</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-line">
                    {visibleApplications.map((application) => (
                      <tr key={application.id}>
                        <td className="py-3"><StatusBadge status={application.status} /></td>
                        <td className="py-3 font-medium text-ink">{application.position}</td>
                        <td className="py-3 text-slate-600">{application.company}</td>
                        <td className="py-3 text-slate-600">{application.score ? `${application.score}%` : "-"}</td>
                        <td className="py-3 text-slate-600">
                          {application.errors || lastLogMessage(application) || (application.url ? "Abrir vacante" : "-")}
                          {application.url ? (
                            <a className="ml-2 font-medium text-brand" href={application.url} target="_blank" rel="noreferrer">
                              Link
                            </a>
                          ) : null}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <EmptyState
                icon={AlertCircle}
                title={hasParsedCv ? "Sin postulaciones en cola" : "Sube tu CV para iniciar"}
                text={hasParsedCv ? "No hay fuentes reales configuradas o no se encontraron vacantes compatibles." : "El sistema iniciara el pipeline automaticamente al recibir el CV."}
              />
            )}
          </section>

          <section className="mt-6 rounded-lg border border-line bg-white p-5 shadow-panel">
            <h2 className="font-semibold text-ink">Procesos recientes</h2>
            <div className="mt-4 space-y-3">
              {tasks.slice(0, 5).map((task) => (
                <div key={task.id} className="rounded-lg border border-line p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="font-medium text-ink">{task.task_name}</span>
                    <StatusBadge status={task.status} />
                  </div>
                  {task.error_message ? <p className="mt-2 text-sm text-rose-700">{task.error_message}</p> : null}
                </div>
              ))}
              {!tasks.length ? <p className="text-sm text-slate-500">Aun no hay procesos registrados.</p> : null}
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function InfoRow({ label, value, status }: { label: string; value: string; status?: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line pb-3 last:border-b-0 last:pb-0">
      <div>
        <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
        <p className="mt-1 text-sm text-ink">{value}</p>
      </div>
      {status ? <StatusBadge status={status} /> : null}
    </div>
  );
}

function Counter({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-line bg-white p-4 shadow-panel">
      <p className="text-sm font-medium text-slate-500">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
    </div>
  );
}

function Notice({ tone, text }: { tone: "error" | "success"; text: string }) {
  const style = tone === "error" ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700";
  return <p className={`mb-4 rounded-lg p-3 text-sm ${style}`}>{text}</p>;
}

function lastLogMessage(application: Application): string | null {
  const last = application.logs.at(-1);
  if (!last) {
    return null;
  }
  return typeof last.message === "string" ? last.message : null;
}
