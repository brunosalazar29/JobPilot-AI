"use client";

import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  FilePlus2,
  Loader2,
  Play,
  RefreshCw,
  Search,
  Square,
  TerminalSquare
} from "lucide-react";
import { ChangeEvent, FormEvent, type ElementType, useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import {
  buildConsoleEntries,
  formatDateTime,
  formatDuration,
  formatRelativeTime,
  getApplicationCurrentMessage,
  getDomainLabel,
  getTaskCurrentMessage,
  getTaskLabel,
  summarizeTaskResult
} from "@/lib/userText";
import type { Application, DetectedProfile, JobMatch, Resume, SearchRun, TaskRun } from "@/types";

type QueueCounts = {
  applied: number;
  failed: number;
  needs_manual_action: number;
  attempting: number;
};

type SearchRunCommandResponse = {
  run: SearchRun;
  task_run_id: number | null;
  message: string;
};

export default function DashboardPage() {
  const [detected, setDetected] = useState<DetectedProfile | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [tasks, setTasks] = useState<TaskRun[]>([]);
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [searchRun, setSearchRun] = useState<SearchRun | null>(null);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploadBusy, setUploadBusy] = useState(false);
  const [runBusy, setRunBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) {
      setLoading(true);
    }
    setError(null);
    try {
      const [profileData, resumeData, applicationData, taskData, matchData, runData] = await Promise.all([
        apiFetch<DetectedProfile>("/profile/detected"),
        apiFetch<Resume[]>("/documents"),
        apiFetch<Application[]>("/applications"),
        apiFetch<TaskRun[]>("/tasks"),
        apiFetch<JobMatch[]>("/matches"),
        apiFetch<SearchRun>("/runs/current")
      ]);
      setDetected(profileData);
      setResumes(resumeData);
      setApplications(applicationData);
      setTasks(taskData);
      setMatches(matchData);
      setSearchRun(runData);
      setLastUpdated(new Date().toISOString());
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
      setError("Selecciona un CV en PDF o DOCX.");
      return;
    }
    setUploadBusy(true);
    setError(null);
    setMessage(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      await apiFetch<Resume>("/documents/upload", { method: "POST", body: formData });
      setFile(null);
      setMessage("CV recibido. Se esta analizando para actualizar tu perfil detectado.");
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo subir el CV");
    } finally {
      setUploadBusy(false);
    }
  }

  async function startSearch() {
    setRunBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await apiFetch<SearchRunCommandResponse>("/runs/start", { method: "POST" });
      setSearchRun(response.run);
      setMessage(response.message);
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar la busqueda");
    } finally {
      setRunBusy(false);
    }
  }

  async function stopSearch() {
    setRunBusy(true);
    setError(null);
    setMessage(null);
    try {
      const response = await apiFetch<SearchRunCommandResponse>("/runs/stop", { method: "POST" });
      setSearchRun(response.run);
      setMessage("Busqueda detenida. Ya puedes cambiar el CV o iniciar otra corrida despues.");
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo detener la busqueda");
    } finally {
      setRunBusy(false);
    }
  }

  const latestResume = resumes[0] ?? null;
  const latestPipeline = tasks.find((task) => task.task_name === "cv_pipeline") ?? null;
  const parseTask =
    tasks.find((task) => task.task_name === "parse_resume" && ["running", "queued"].includes(task.status)) ?? null;
  const searchActive = searchRun?.status === "running";
  const cvReady = latestResume?.status === "parsed";
  const activeApplication =
    applications.find((application) => ["queued", "preparing", "applying", "matched"].includes(application.status)) ?? null;
  const consoleEntries = useMemo(() => buildConsoleEntries(tasks, applications), [tasks, applications]);

  const queueCounts = useMemo<QueueCounts>(() => {
    return applications.reduce(
      (counts, application) => {
        if (application.status === "applied") {
          counts.applied += 1;
        }
        if (application.status === "failed") {
          counts.failed += 1;
        }
        if (application.status === "needs_manual_action") {
          counts.needs_manual_action += 1;
        }
        if (["queued", "preparing", "applying", "ready_for_review", "matched"].includes(application.status)) {
          counts.attempting += 1;
        }
        return counts;
      },
      { applied: 0, failed: 0, needs_manual_action: 0, attempting: 0 }
    );
  }, [applications]);

  const foundJobs = typeof latestPipeline?.result.jobs_collected === "number" ? latestPipeline.result.jobs_collected : 0;
  const matchedJobs =
    typeof latestPipeline?.result.matches_created === "number" ? latestPipeline.result.matches_created : matches.length;
  const queueItems =
    typeof latestPipeline?.result.queue_items_created === "number"
      ? latestPipeline.result.queue_items_created
      : applications.length;

  const latestTaskSummary = latestPipeline ? summarizeTaskResult(latestPipeline) : null;
  const latestFailure = tasks.find((task) => task.status === "failed") ?? null;
  const readyToSearchMessage = "Tu CV ya fue analizado. Usa el boton de iniciar busqueda y postulacion cuando quieras.";
  const statusTitle = parseTask
    ? getTaskLabel(parseTask.task_name)
    : searchActive
      ? searchRun?.current_stage ?? "Busqueda en curso"
      : searchRun?.status === "completed"
        ? "Busqueda completada"
        : searchRun?.status === "stopped"
          ? "Busqueda detenida"
          : searchRun?.status === "failed"
            ? "Busqueda detenida por error"
            : cvReady
              ? "Listo para buscar"
              : "Sin actividad en curso";
  const statusDescription = parseTask
    ? getTaskCurrentMessage(parseTask)
    : searchRun?.current_message ?? latestTaskSummary ?? "Sube tu CV para preparar tu perfil y luego inicia la busqueda.";
  const visibleStatusDescription =
    !parseTask && !searchActive && cvReady && searchRun?.status === "idle" ? readyToSearchMessage : statusDescription;
  const elapsedTime = parseTask
    ? formatDuration(parseTask.started_at, parseTask.completed_at)
    : searchActive
      ? formatDuration(searchRun?.started_at)
      : latestPipeline
        ? formatDuration(latestPipeline.started_at, latestPipeline.completed_at)
        : "-";
  const currentVacancy = activeApplication
    ? `${activeApplication.company} · ${getDomainLabel(activeApplication.url)}`
    : searchActive
      ? "Buscando o evaluando vacantes"
      : "Sin vacante activa";
  const mainStatus = parseTask ? parseTask.status : searchRun?.status ?? "idle";
  const latestMessage = activeApplication
    ? getApplicationCurrentMessage(activeApplication)
    : parseTask
      ? getTaskCurrentMessage(parseTask)
      : !searchActive && cvReady && searchRun?.status === "idle"
        ? readyToSearchMessage
        : searchRun?.current_message ?? latestTaskSummary ?? "Sin ejecucion reciente.";

  return (
    <div>
      <PageHeader
        title="Panel de actividad"
        description="Primero sube tu CV para actualizar el perfil. Luego inicia o detiene la busqueda y postulacion desde este panel."
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
        Actualizacion automatica cada 4 segundos
        {lastUpdated ? ` · Ultima actualizacion ${formatRelativeTime(lastUpdated)} (${formatDateTime(lastUpdated)})` : ""}
      </p>

      {error ? <Notice tone="error" text={error} /> : null}
      {message ? <Notice tone="success" text={message} /> : null}
      {searchRun?.last_error ? <Notice tone="error" text={searchRun.last_error} /> : null}
      {latestFailure?.error_message ? <Notice tone="error" text={latestFailure.error_message} /> : null}

      <section className="grid gap-4 xl:grid-cols-[1.2fr_0.8fr]">
        <form onSubmit={upload} className="rounded-lg border border-line bg-white p-5 shadow-panel">
          <h2 className="font-semibold text-ink">CV principal</h2>
          <p className="mt-2 text-sm text-slate-600">
            El CV se usa para llenar tu base de datos de candidato, detectar tu perfil y preparar las busquedas futuras.
          </p>
          <div className="mt-4 flex flex-col gap-4 lg:flex-row lg:items-end">
            <label className="flex-1 text-sm font-medium text-slate-700">
              Archivo PDF o DOCX
              <input
                type="file"
                accept=".pdf,.docx"
                onChange={selectFile}
                disabled={searchActive || uploadBusy || runBusy}
                className="mt-2 w-full rounded-lg border border-line bg-white px-3 py-2 text-sm disabled:cursor-not-allowed disabled:bg-slate-100"
              />
            </label>
            <button
              type="submit"
              disabled={searchActive || uploadBusy || runBusy}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {uploadBusy ? <Loader2 className="h-4 w-4 animate-spin" /> : <FilePlus2 className="h-4 w-4" />}
              Subir CV
            </button>
          </div>
          <div className="mt-4 rounded-lg bg-slate-50 p-4 text-sm text-slate-600">
            <p className="font-medium text-ink">{latestResume?.original_filename ?? "Aun no hay CV cargado."}</p>
            {latestResume ? (
              <div className="mt-2 flex flex-wrap items-center gap-3">
                <StatusBadge status={latestResume.status} />
                <span>{latestResume.parsed_at ? `Actualizado ${formatRelativeTime(latestResume.parsed_at)}` : "Analisis pendiente"}</span>
              </div>
            ) : null}
            <p className="mt-3 text-xs text-slate-500">
              {searchActive
                ? "La busqueda esta activa. Detenla antes de reemplazar el CV."
                : cvReady
                  ? "El CV ya esta listo. Usa el boton de iniciar busqueda cuando quieras lanzar la cola."
                  : "Sube o termina de analizar el CV antes de iniciar la busqueda."}
            </p>
          </div>
        </form>

        <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-semibold text-ink">{statusTitle}</h2>
              <p className="mt-2 text-sm text-slate-600">{visibleStatusDescription}</p>
            </div>
            <StatusBadge status={mainStatus} />
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <MetricCard label="Tiempo en proceso" value={elapsedTime} />
            <MetricCard label="Vacante actual" value={currentVacancy} />
          </div>
          <div className="mt-4 rounded-lg border border-line bg-slate-50 p-4">
            <p className="text-xs font-semibold uppercase text-slate-500">Ultimo mensaje</p>
            <p className="mt-2 text-sm text-ink">{latestMessage}</p>
          </div>
          <div className="mt-4 flex flex-wrap gap-3">
            <button
              type="button"
              onClick={() => void startSearch()}
              disabled={!cvReady || searchActive || uploadBusy || runBusy}
              className="inline-flex items-center justify-center gap-2 rounded-lg bg-ink px-4 py-2.5 text-sm font-semibold text-white disabled:cursor-not-allowed disabled:opacity-60"
            >
              {runBusy && !searchActive ? <Loader2 className="h-4 w-4 animate-spin" /> : <Play className="h-4 w-4" />}
              Iniciar busqueda y postulacion
            </button>
            <button
              type="button"
              onClick={() => void stopSearch()}
              disabled={!searchActive || uploadBusy || runBusy}
              className="inline-flex items-center justify-center gap-2 rounded-lg border border-rose-200 bg-rose-50 px-4 py-2.5 text-sm font-semibold text-rose-700 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {runBusy && searchActive ? <Loader2 className="h-4 w-4 animate-spin" /> : <Square className="h-4 w-4" />}
              Detener busqueda
            </button>
          </div>
        </div>
      </section>

      {loading ? (
        <div className="mt-6 flex items-center gap-2 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          Cargando actividad...
        </div>
      ) : (
        <>
          <section className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-6">
            <Counter label="Vacantes encontradas" value={foundJobs} icon={Search} />
            <Counter label="Compatibles" value={matchedJobs} icon={CheckCircle2} />
            <Counter label="En cola o intento" value={queueItems || queueCounts.attempting} icon={Clock3} />
            <Counter label="Enviadas" value={queueCounts.applied} icon={CheckCircle2} />
            <Counter label="Revision manual" value={queueCounts.needs_manual_action} icon={AlertCircle} />
            <Counter label="Fallidas" value={queueCounts.failed} icon={AlertCircle} />
          </section>

          <section className="mt-6 grid gap-4 xl:grid-cols-[0.9fr_1.1fr]">
            <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
              <h2 className="font-semibold text-ink">Perfil detectado</h2>
              <div className="mt-4 space-y-4">
                <InfoRow label="Completitud" value={detected ? `${detected.completeness}%` : "-"} />
                <InfoRow label="Nombre" value={detected?.profile.full_name ?? "No detectado"} />
                <InfoRow label="Correo del CV" value={detected?.profile.email ?? "No detectado"} />
                <InfoRow
                  label="Roles objetivo"
                  value={detected?.profile.target_roles?.length ? detected.profile.target_roles.join(", ") : "Aun no inferidos"}
                />
                <InfoRow
                  label="Skills principales"
                  value={detected?.profile.skills?.slice(0, 8).join(", ") || "No detectadas"}
                />
              </div>
            </div>

            <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
              <h2 className="font-semibold text-ink">Campos faltantes utiles</h2>
              <p className="mt-2 text-sm text-slate-600">No bloquean el flujo. Solo mejoran matching o algunos formularios.</p>
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
                    El perfil tiene informacion suficiente para seguir buscando y postulando.
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className="mt-6 grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
            <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
              <div className="mb-4">
                <h2 className="font-semibold text-ink">Seguimiento de vacantes</h2>
                <p className="mt-1 text-sm text-slate-600">
                  Aqui ves que vacantes se estan intentando y por que se detienen.
                </p>
              </div>

              {applications.length ? (
                <div className="space-y-3">
                  {applications.slice(0, 6).map((application) => (
                    <article key={application.id} className="rounded-lg border border-line p-4">
                      <div className="flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <p className="font-semibold text-ink">{application.position}</p>
                          <p className="mt-1 text-sm text-slate-600">
                            {application.company} · {getDomainLabel(application.url)}
                          </p>
                        </div>
                        <StatusBadge status={application.status} />
                      </div>
                      <div className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-[120px_1fr]">
                        <span className="font-medium text-slate-500">Estado actual</span>
                        <span>{getApplicationCurrentMessage(application)}</span>
                        <span className="font-medium text-slate-500">Score</span>
                        <span>{application.score ? `${application.score}%` : "Sin score"}</span>
                        <span className="font-medium text-slate-500">Ultimo cambio</span>
                        <span>{formatRelativeTime(application.created_at)}</span>
                      </div>
                    </article>
                  ))}
                </div>
              ) : (
                <EmptyState
                  icon={AlertCircle}
                  title={cvReady ? "Sin vacantes en seguimiento" : "Primero prepara el CV"}
                  text={
                    cvReady
                      ? searchActive
                        ? "La busqueda esta corriendo. Aqui apareceran las vacantes apenas entren a la cola."
                        : "Tu CV ya esta listo. Usa el boton de iniciar busqueda para lanzar la cola."
                      : "Sube tu CV y espera a que termine el analisis."
                  }
                />
              )}
            </div>

            <div className="rounded-lg border border-line bg-slate-950 p-5 text-slate-100 shadow-panel">
              <div className="flex items-center gap-2">
                <TerminalSquare className="h-5 w-5 text-emerald-300" />
                <h2 className="font-semibold">Consola de actividad</h2>
              </div>
              <p className="mt-2 text-sm text-slate-400">Muestra lo ultimo que hizo el sistema, con hora y etapa.</p>
              <div className="mt-4 max-h-[420px] space-y-3 overflow-auto rounded-lg border border-slate-800 bg-slate-950/80 p-3">
                {consoleEntries.length ? (
                  consoleEntries.map((entry) => (
                    <div key={entry.key} className="border-b border-slate-800 pb-3 last:border-b-0 last:pb-0">
                      <div className="flex flex-wrap items-center gap-2 text-xs text-slate-400">
                        <span>{formatDateTime(entry.timestamp)}</span>
                        <span>·</span>
                        <span>{formatRelativeTime(entry.timestamp)}</span>
                        <span>·</span>
                        <span>{entry.title}</span>
                      </div>
                      <p className="mt-1 text-sm text-slate-100">{entry.detail}</p>
                    </div>
                  ))
                ) : (
                  <p className="text-sm text-slate-400">Todavia no hay actividad registrada.</p>
                )}
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-line pb-3 last:border-b-0 last:pb-0">
      <div>
        <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
        <p className="mt-1 text-sm text-ink">{value}</p>
      </div>
    </div>
  );
}

function Counter({ label, value, icon: Icon }: { label: string; value: number; icon: ElementType }) {
  return (
    <div className="rounded-lg border border-line bg-white p-4 shadow-panel">
      <div className="flex items-center justify-between gap-3">
        <p className="text-sm font-medium text-slate-500">{label}</p>
        <Icon className="h-4 w-4 text-slate-400" />
      </div>
      <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-line bg-slate-50 p-3">
      <p className="text-xs font-semibold uppercase text-slate-500">{label}</p>
      <p className="mt-2 text-sm font-medium text-ink">{value}</p>
    </div>
  );
}

function Notice({ tone, text }: { tone: "error" | "success"; text: string }) {
  const style = tone === "error" ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700";
  return <p className={`mb-4 rounded-lg p-3 text-sm ${style}`}>{text}</p>;
}
