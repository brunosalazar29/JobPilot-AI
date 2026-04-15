"use client";

import { ArrowLeft, ClipboardCheck, FileText, Loader2, WandSparkles } from "lucide-react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import type { Application, Job, JobMatch, Resume } from "@/types";

export default function JobDetailPage() {
  const params = useParams<{ id: string }>();
  const jobId = Number(params.id);
  const [job, setJob] = useState<Job | null>(null);
  const [match, setMatch] = useState<JobMatch | null>(null);
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [resumeId, setResumeId] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      setLoading(true);
      try {
        const [jobData, resumeData] = await Promise.all([apiFetch<Job>(`/jobs/${jobId}`), apiFetch<Resume[]>("/documents")]);
        setJob(jobData);
        setResumes(resumeData);
        setResumeId(resumeData[0]?.id.toString() ?? "");
        try {
          const matchData = await apiFetch<JobMatch>(`/matches/jobs/${jobId}`);
          setMatch(matchData);
        } catch {
          setMatch(null);
        }
      } catch (err) {
        setError(err instanceof Error ? err.message : "No se pudo cargar la vacante");
      } finally {
        setLoading(false);
      }
    }
    if (Number.isFinite(jobId)) {
      void load();
    }
  }, [jobId]);

  async function generateCoverLetter() {
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/documents/generate", {
        method: "POST",
        body: JSON.stringify({
          kind: "cover_letter",
          job_id: jobId,
          resume_id: resumeId ? Number(resumeId) : null
        })
      });
      setMessage("Cover letter encolada");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar cover letter");
    } finally {
      setBusy(false);
    }
  }

  async function prepareApplication() {
    if (!job) {
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const application = await apiFetch<Application>("/applications", {
        method: "POST",
        body: JSON.stringify({
          job_id: job.id,
          resume_id: resumeId ? Number(resumeId) : null
        })
      });
      await apiFetch(`/applications/${application.id}/prepare`, { method: "POST" });
      setMessage("Aplicación creada y preparación encolada para revisión manual");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo preparar la aplicación");
    } finally {
      setBusy(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-sm text-slate-600">
        <Loader2 className="h-4 w-4 animate-spin" />
        Cargando vacante...
      </div>
    );
  }

  if (!job) {
    return (
      <div>
        <Link href="/jobs" className="inline-flex items-center gap-2 text-sm font-medium text-brand">
          <ArrowLeft className="h-4 w-4" />
          Volver
        </Link>
        <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error ?? "Vacante no encontrada"}</p>
      </div>
    );
  }

  return (
    <div>
      <Link href="/jobs" className="mb-4 inline-flex items-center gap-2 text-sm font-medium text-brand">
        <ArrowLeft className="h-4 w-4" />
        Volver a vacantes
      </Link>
      <PageHeader
        title={job.title}
        description={`${job.company} · ${job.location ?? "Ubicación no especificada"} · ${job.remote_type ?? "modalidad abierta"}`}
        action={
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => void generateCoverLetter()}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-lg border border-line bg-white px-4 py-2 text-sm font-semibold text-ink disabled:opacity-60"
            >
              <WandSparkles className="h-4 w-4" />
              Cover letter
            </button>
            <button
              type="button"
              onClick={() => void prepareApplication()}
              disabled={busy}
              className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
            >
              {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <ClipboardCheck className="h-4 w-4" />}
              Preparar aplicación
            </button>
          </div>
        }
      />

      {error ? <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}
      {message ? <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">{message}</p> : null}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          <h2 className="font-semibold text-ink">Descripción</h2>
          <p className="mt-3 whitespace-pre-line text-sm leading-7 text-slate-600">{job.description}</p>
          <div className="mt-5 flex flex-wrap gap-2">
            {job.technologies.map((technology) => (
              <span key={technology} className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
                {technology}
              </span>
            ))}
          </div>
          <label className="mt-6 block text-sm font-medium text-slate-700">
            CV para esta aplicación
            <select
              value={resumeId}
              onChange={(event) => setResumeId(event.target.value)}
              className="mt-2 w-full rounded-lg border border-line px-3 py-2 outline-none focus:border-brand"
            >
              <option value="">Sin CV seleccionado</option>
              {resumes.map((resume) => (
                <option key={resume.id} value={resume.id}>
                  {resume.original_filename}
                </option>
              ))}
            </select>
          </label>
        </section>

        <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="font-semibold text-ink">Compatibilidad</h2>
              <p className="mt-2 text-sm text-slate-600">{match?.summary ?? "Ejecuta matching para ver explicación."}</p>
            </div>
            {match ? <span className="text-3xl font-semibold text-brand">{match.score}%</span> : <StatusBadge status="pending" />}
          </div>

          <div className="mt-5 space-y-3">
            {Object.entries(match?.criteria ?? {}).map(([name, value]) => (
              <div key={name}>
                <div className="mb-1 flex justify-between text-sm">
                  <span className="capitalize text-slate-600">{name}</span>
                  <span className="font-medium text-ink">{Math.round(value)}</span>
                </div>
                <div className="h-2 rounded-full bg-slate-100">
                  <div className="h-2 rounded-full bg-brand" style={{ width: `${Math.min(100, value * 2)}%` }} />
                </div>
              </div>
            ))}
          </div>

          <div className="mt-6">
            <h3 className="font-medium text-ink">Faltantes</h3>
            <div className="mt-3 flex flex-wrap gap-2">
              {match?.missing_keywords?.length ? (
                match.missing_keywords.map((keyword) => (
                  <span key={keyword} className="rounded-full bg-orange-100 px-3 py-1 text-xs font-semibold text-orange-800">
                    {keyword}
                  </span>
                ))
              ) : (
                <span className="text-sm text-slate-500">Sin faltantes registrados.</span>
              )}
            </div>
          </div>

          <div className="mt-6 rounded-lg bg-slate-50 p-4">
            <div className="flex items-center gap-2 font-medium text-ink">
              <FileText className="h-4 w-4" />
              Respuestas sugeridas
            </div>
            <p className="mt-2 text-sm leading-6 text-slate-600">
              Al preparar la aplicación se generan respuestas para presentación, motivación y pitch corto. Puedes
              revisarlas desde el historial antes del envío final.
            </p>
          </div>
        </section>
      </div>
    </div>
  );
}
