"use client";

import { FilePlus2, FileText, Loader2, RefreshCw, WandSparkles } from "lucide-react";
import { ChangeEvent, FormEvent, useEffect, useState } from "react";

import { EmptyState } from "@/components/EmptyState";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import type { Resume } from "@/types";

type GeneratedDocument = {
  id: number;
  kind: string;
  title: string;
  content: string;
  status: string;
  created_at: string;
};

export default function DocumentsPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [generated, setGenerated] = useState<GeneratedDocument[]>([]);
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function load() {
    setLoading(true);
    try {
      const [resumeData, generatedData] = await Promise.all([
        apiFetch<Resume[]>("/documents"),
        apiFetch<GeneratedDocument[]>("/documents/generated/list")
      ]);
      setResumes(resumeData);
      setGenerated(generatedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron cargar documentos");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  function selectFile(event: ChangeEvent<HTMLInputElement>) {
    setFile(event.target.files?.[0] ?? null);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError("Selecciona un archivo PDF o DOCX");
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
      setMessage("CV subido correctamente. El análisis automático ya fue encolado.");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo subir el CV");
    } finally {
      setBusy(false);
    }
  }

  async function queueParse(resumeId: number) {
    setBusy(true);
    setError(null);
    try {
      await apiFetch(`/documents/${resumeId}/parse`, { method: "POST" });
      setMessage("Parseo encolado");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo encolar el parseo");
    } finally {
      setBusy(false);
    }
  }

  async function generateCoverLetter(resumeId: number) {
    setBusy(true);
    setError(null);
    try {
      await apiFetch("/documents/generate", {
        method: "POST",
        body: JSON.stringify({ kind: "cover_letter", resume_id: resumeId })
      });
      setMessage("Generación encolada");
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo generar documento");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Documentos"
        description="Carga tu CV; JobPilot AI lo analiza y lo usa como base del perfil detectado."
      />

      <form onSubmit={upload} className="mb-6 rounded-lg border border-line bg-white p-5 shadow-panel">
        <div className="flex flex-col gap-4 md:flex-row md:items-end">
          <label className="flex-1 text-sm font-medium text-slate-700">
            CV en PDF o DOCX
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
            Subir CV
          </button>
        </div>
      </form>

      {error ? <p className="mb-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}
      {message ? <p className="mb-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-700">{message}</p> : null}

      <section className="rounded-lg border border-line bg-white p-5 shadow-panel">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-semibold text-ink">CVs cargados</h2>
          <button onClick={() => void load()} className="inline-flex items-center gap-2 text-sm font-medium text-brand">
            <RefreshCw className="h-4 w-4" />
            Actualizar
          </button>
        </div>
        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-600">
            <Loader2 className="h-4 w-4 animate-spin" />
            Cargando...
          </div>
        ) : resumes.length ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="py-2">Archivo</th>
                  <th className="py-2">Estado</th>
                  <th className="py-2">Skills</th>
                  <th className="py-2">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {resumes.map((resume) => (
                  <tr key={resume.id}>
                    <td className="py-3 font-medium text-ink">{resume.original_filename}</td>
                    <td className="py-3">
                      <StatusBadge status={resume.status} />
                    </td>
                    <td className="py-3 text-slate-600">{resume.parsed_resume?.skills?.slice(0, 5).join(", ") || "-"}</td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-2">
                        <button
                          type="button"
                          onClick={() => void queueParse(resume.id)}
                          className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 font-medium text-slate-700"
                        >
                          <RefreshCw className="h-4 w-4" />
                          Analizar otra vez
                        </button>
                        <button
                          type="button"
                          onClick={() => void generateCoverLetter(resume.id)}
                          className="inline-flex items-center gap-2 rounded-lg border border-line px-3 py-1.5 font-medium text-slate-700"
                        >
                          <WandSparkles className="h-4 w-4" />
                          Cover letter
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState icon={FileText} title="Sin CVs" text="Sube un documento para iniciar parsing y matching." />
        )}
      </section>

      <section className="mt-6 rounded-lg border border-line bg-white p-5 shadow-panel">
        <h2 className="font-semibold text-ink">Documentos generados</h2>
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          {generated.map((document) => (
            <article key={document.id} className="rounded-lg border border-line p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold text-ink">{document.title}</h3>
                  <p className="mt-1 text-xs uppercase text-slate-500">{document.kind}</p>
                </div>
                <StatusBadge status={document.status} />
              </div>
              <p className="mt-3 line-clamp-5 whitespace-pre-line text-sm leading-6 text-slate-600">{document.content}</p>
            </article>
          ))}
          {!generated.length ? <p className="text-sm text-slate-500">No hay documentos generados todavía.</p> : null}
        </div>
      </section>
    </div>
  );
}
