"use client";

import { BriefcaseBusiness, Loader2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { useEffect, useMemo, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { apiFetch } from "@/lib/api";
import type { Job, JobMatch } from "@/types";

export default function JobsPage() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [matches, setMatches] = useState<JobMatch[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    setError(null);
    try {
      const [jobsData, matchData] = await Promise.all([apiFetch<Job[]>("/jobs"), apiFetch<JobMatch[]>("/matches")]);
      setJobs(jobsData);
      setMatches(matchData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar vacantes");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  const scoreByJobId = useMemo(() => new Map(matches.map((match) => [match.job_id, match.score])), [matches]);

  return (
    <div>
      <PageHeader
        title="Vacantes encontradas"
        description="Lista generada por las fuentes configuradas después de subir el CV."
        action={
          <button onClick={() => void load()} className="inline-flex items-center gap-2 rounded-lg border border-line px-4 py-2 text-sm font-semibold text-ink">
            <RefreshCw className="h-4 w-4" />
            Actualizar
          </button>
        }
      />

      {error ? <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}

      <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando vacantes...
          </div>
        ) : jobs.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="py-2">Score</th>
                  <th className="py-2">Puesto</th>
                  <th className="py-2">Empresa</th>
                  <th className="py-2">Modalidad</th>
                  <th className="py-2">Link</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {jobs.map((job) => (
                  <tr key={job.id}>
                    <td className="py-3 font-semibold text-brand">{formatScore(scoreByJobId.get(job.id))}</td>
                    <td className="py-3 font-medium text-ink">{job.title}</td>
                    <td className="py-3 text-slate-600">{job.company}</td>
                    <td className="py-3 text-slate-600">{job.remote_type ?? "-"}</td>
                    <td className="py-3">
                      {job.url ? (
                        <a className="font-medium text-brand" href={job.url} target="_blank" rel="noreferrer">
                          Abrir
                        </a>
                      ) : (
                        <Link className="font-medium text-brand" href={`/jobs/${job.id}`}>
                          Detalle
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            icon={BriefcaseBusiness}
            title="Sin vacantes reales"
            text="Configura una fuente de vacantes para que el pipeline pueda recolectar empleos después de analizar el CV."
          />
        )}
      </section>
    </div>
  );
}

function formatScore(score: number | undefined): string {
  return score === undefined ? "-" : `${score}%`;
}
