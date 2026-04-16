"use client";

import { ClipboardList, ExternalLink, Loader2, RefreshCw, RotateCcw } from "lucide-react";
import Image from "next/image";
import { useCallback, useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import {
  formatDateTime,
  formatRelativeTime,
  getApplicationCurrentMessage,
  getDomainLabel,
  getLatestEvidence,
  getLatestTimestamp,
  getManualActionGuidance,
  translateLogMessage
} from "@/lib/userText";
import type { Application, JobMatch } from "@/types";

export default function ApplicationsPage() {
  const [applications, setApplications] = useState<Application[]>([]);
  const [matches, setMatches] = useState<JobMatch[]>([]);
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
    setError(null);
    try {
      const [applicationData, matchData] = await Promise.all([
        apiFetch<Application[]>("/applications"),
        apiFetch<JobMatch[]>("/matches")
      ]);
      setApplications(applicationData);
      setMatches(matchData);
      setSelected((current) => applicationData.find((item) => item.id === current?.id) ?? applicationData[0] ?? null);
      setLastUpdated(new Date().toISOString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el seguimiento");
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

  async function retry(applicationId: number) {
    setBusy(true);
    setError(null);
    setMessage(null);
    try {
      await apiFetch(`/applications/${applicationId}/prepare`, { method: "POST" });
      setMessage("Se volvió a encolar el intento de formulario.");
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo reintentar la postulación");
    } finally {
      setBusy(false);
    }
  }

  const matchByJobId = useMemo(() => new Map(matches.map((match) => [match.job_id, match])), [matches]);

  return (
    <div>
      <PageHeader
        title="Seguimiento de postulaciones"
        description="Aquí ves qué vacante se intentó, cómo quedó y qué hacer si necesita intervención manual."
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

      {error ? <Notice tone="error" text={error} /> : null}
      {message ? <Notice tone="success" text={message} /> : null}

      <div className="grid gap-6 xl:grid-cols-[0.95fr_1.05fr]">
        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold text-ink">Vacantes en seguimiento</h2>
              <p className="mt-1 text-sm text-slate-600">Se actualiza solo mientras el sistema trabaja.</p>
            </div>
          </div>

          {loading ? (
            <div className="flex items-center gap-2 text-sm text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin" />
              Cargando seguimiento...
            </div>
          ) : applications.length ? (
            <div className="space-y-3">
              {applications.map((application) => {
                const match = application.job_id ? matchByJobId.get(application.job_id) : null;
                const changedAt = getLatestTimestamp(application.logs) ?? application.created_at;
                return (
                  <button
                    key={application.id}
                    type="button"
                    onClick={() => setSelected(application)}
                    className="w-full rounded-lg border border-line p-4 text-left transition hover:border-brand"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div>
                        <p className="font-semibold text-ink">{application.position}</p>
                        <p className="mt-1 text-sm text-slate-600">
                          {application.company} · {getDomainLabel(application.url)}
                        </p>
                      </div>
                      <StatusBadge status={application.status} />
                    </div>
                    <div className="mt-3 grid gap-2 text-sm text-slate-600">
                      <p>{getApplicationCurrentMessage(application)}</p>
                      <div className="flex flex-wrap gap-3 text-xs text-slate-500">
                        <span>Score: {application.score ? `${application.score}%` : "Sin score"}</span>
                        <span>{match?.summary ?? "Compatibilidad calculada desde tu CV"}</span>
                        <span>Actualizado {formatRelativeTime(changedAt)}</span>
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          ) : (
            <EmptyState
              icon={ClipboardList}
              title="Sin postulaciones"
              text="Cuando aparezcan vacantes compatibles, verás aquí cada intento y su estado."
            />
          )}
        </section>

        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          {selected ? (
            <ApplicationDetail
              application={selected}
              match={selected.job_id ? matchByJobId.get(selected.job_id) ?? null : null}
              busy={busy}
              onRetry={retry}
            />
          ) : (
            <EmptyState
              icon={ClipboardList}
              title="Selecciona una vacante"
              text="El detalle mostrará evidencia, motivo del estado actual y qué hacer si requiere revisión manual."
            />
          )}
        </section>
      </div>
    </div>
  );
}

function ApplicationDetail({
  application,
  match,
  busy,
  onRetry
}: {
  application: Application;
  match: JobMatch | null;
  busy: boolean;
  onRetry: (applicationId: number) => Promise<void>;
}) {
  const evidence = getLatestEvidence(application);
  const changedAt = getLatestTimestamp(application.logs) ?? application.created_at;
  const manualGuidance = getManualActionGuidance(application);

  return (
    <>
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="font-semibold text-ink">{application.position}</h2>
          <p className="mt-1 text-sm text-slate-600">
            {application.company} · {getDomainLabel(application.url)}
          </p>
        </div>
        <StatusBadge status={application.status} />
      </div>

      <div className="mt-5 flex flex-wrap gap-2">
        <button
          type="button"
          disabled={busy}
          onClick={() => void onRetry(application.id)}
          className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
        >
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
          Reintentar
        </button>
        {application.url ? (
          <a
            href={application.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm font-semibold text-ink"
          >
            <ExternalLink className="h-4 w-4" />
            Abrir vacante
          </a>
        ) : null}
        {evidence.url ? (
          <a
            href={evidence.url}
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm font-semibold text-ink"
          >
            <ExternalLink className="h-4 w-4" />
            Ver evidencia
          </a>
        ) : null}
      </div>

      <dl className="mt-5 grid gap-3 text-sm sm:grid-cols-2">
        <Info label="Estado actual" value={getApplicationCurrentMessage(application)} />
        <Info label="Último cambio" value={`${formatRelativeTime(changedAt)} (${formatDateTime(changedAt)})`} />
        <Info label="Score de compatibilidad" value={application.score ? `${application.score}%` : "Sin score"} />
        <Info label="Dominio" value={getDomainLabel(application.url)} />
        <Info label="Motivo de match" value={match?.summary ?? "Compatibilidad calculada desde tu CV y tus skills."} />
        <Info label="Palabras faltantes" value={match?.missing_keywords?.length ? match.missing_keywords.join(", ") : "Sin faltantes relevantes"} />
      </dl>

      {manualGuidance ? <Notice tone="warning" text={manualGuidance} /> : null}
      {application.errors && application.status !== "needs_manual_action" ? <Notice tone="error" text={application.errors} /> : null}

      {evidence.url ? (
        <div className="mt-6">
          <h3 className="font-medium text-ink">Evidencia del intento</h3>
          <p className="mt-1 text-sm text-slate-600">{evidence.label}</p>
          <div className="mt-3 overflow-hidden rounded-lg border border-line bg-slate-50">
            <Image
              src={evidence.url}
              alt={evidence.label ?? "Evidencia"}
              width={1280}
              height={900}
              className="h-auto w-full object-cover"
              unoptimized
            />
          </div>
        </div>
      ) : null}

      <div className="mt-6">
        <h3 className="font-medium text-ink">Actividad de esta vacante</h3>
        <div className="mt-3 space-y-3 rounded-lg border border-line bg-slate-50 p-4">
          {application.logs.length ? (
            [...application.logs]
              .reverse()
              .slice(0, 10)
              .map((log, index) => (
                <div key={index} className="border-b border-line pb-3 text-sm last:border-b-0 last:pb-0">
                        <p className="font-medium text-ink">
                          {typeof log.message === "string" ? translateLogMessage(log.message) ?? log.message : "Evento registrado"}
                        </p>
                  {typeof log.timestamp === "string" ? (
                    <p className="mt-1 text-xs text-slate-500">
                      {formatDateTime(log.timestamp)} · {formatRelativeTime(log.timestamp)}
                    </p>
                  ) : null}
                </div>
              ))
          ) : (
            <p className="text-sm text-slate-500">Aún no hay eventos registrados para esta vacante.</p>
          )}
        </div>
      </div>
    </>
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

function Notice({ tone, text }: { tone: "error" | "success" | "warning"; text: string }) {
  const style =
    tone === "error"
      ? "bg-rose-50 text-rose-700"
      : tone === "warning"
        ? "mt-5 bg-amber-50 text-amber-800"
        : "bg-emerald-50 text-emerald-700";
  return <p className={`mt-5 rounded-lg p-3 text-sm ${style}`}>{text}</p>;
}
