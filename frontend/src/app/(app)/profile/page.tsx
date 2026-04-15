"use client";

import { AlertCircle, CheckCircle2, FileText, Loader2, Save, Sparkles } from "lucide-react";
import Link from "next/link";
import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";

import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { apiFetch } from "@/lib/api";
import type { DetectedProfile, DetectedProfileField, Profile } from "@/types";

type MissingForm = Record<string, string>;

const editableFields: Record<string, { label: string; type?: string; placeholder?: string }> = {
  full_name: { label: "Nombre" },
  email: { label: "Email", type: "email" },
  phone: { label: "Teléfono" },
  location: { label: "Ubicación" },
  linkedin_url: { label: "LinkedIn" },
  github_url: { label: "GitHub" },
  portfolio_url: { label: "Portafolio" },
  preferred_modality: { label: "Modalidad preferida", placeholder: "remote, hybrid u onsite" },
  salary_expectation: { label: "Expectativa salarial", type: "number" },
  salary_currency: { label: "Moneda", placeholder: "USD, PEN, EUR" }
};

export default function ProfilePage() {
  const [detected, setDetected] = useState<DetectedProfile | null>(null);
  const [form, setForm] = useState<MissingForm>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [dirty, setDirty] = useState(false);

  const load = useCallback(async (showSpinner = false) => {
    if (showSpinner) {
      setLoading(true);
    }
    setError(null);
    try {
      const data = await apiFetch<DetectedProfile>("/profile/detected");
      setDetected(data);
      if (!dirty) {
        setForm(buildInitialForm(data));
      }
      setLastUpdated(new Date().toLocaleTimeString());
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo cargar el perfil detectado");
    } finally {
      if (showSpinner) {
        setLoading(false);
      }
    }
  }, [dirty]);

  useEffect(() => {
    void load(true);
    const intervalId = window.setInterval(() => {
      void load(false);
    }, 4000);
    return () => window.clearInterval(intervalId);
  }, [load]);

  const editableMissing = useMemo(() => {
    return (detected?.missing_fields ?? []).filter((field) => field in editableFields);
  }, [detected]);

  function update(field: string, value: string) {
    setDirty(true);
    setForm((current) => ({ ...current, [field]: value }));
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const payload: Record<string, string | number | null> = {};
      for (const [field, value] of Object.entries(form)) {
        if (!value.trim()) {
          continue;
        }
        payload[field] = field === "salary_expectation" ? Number(value) : value.trim();
      }
      if (!Object.keys(payload).length) {
        setMessage("No hay datos nuevos para guardar");
        return;
      }
      await apiFetch<Profile>("/profile", {
        method: "PUT",
        body: JSON.stringify(payload)
      });
      setMessage("Datos faltantes guardados");
      setDirty(false);
      await load(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudieron guardar los datos");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <PageHeader
        title="Perfil detectado"
        description="El CV es la fuente principal. Revisa lo que el sistema entendió y completa solo lo que falte si te ayuda."
        action={
          <Link className="rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white" href="/documents">
            Subir CV
          </Link>
        }
      />
      <p className="mb-4 text-xs font-medium text-slate-500">
        Actualizacion automatica cada 4 segundos{lastUpdated ? ` - Ultima lectura: ${lastUpdated}` : ""}.
      </p>

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          Analizando perfil...
        </div>
      ) : detected ? (
        <>
          {error ? <Notice tone="error" text={error} /> : null}
          {message ? <Notice tone="success" text={message} /> : null}

          <section className="grid gap-4 lg:grid-cols-[0.8fr_1.2fr]">
            <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-slate-500">Completitud detectada</p>
                  <p className="mt-2 text-4xl font-semibold text-ink">{detected.completeness}%</p>
                </div>
                <Sparkles className="h-6 w-6 text-brand" />
              </div>
              <div className="mt-5 h-2 rounded-full bg-slate-100">
                <div className="h-2 rounded-full bg-brand" style={{ width: `${detected.completeness}%` }} />
              </div>

              <div className="mt-6 rounded-lg bg-slate-50 p-4">
                <div className="flex items-center gap-2 font-medium text-ink">
                  <FileText className="h-4 w-4" />
                  CV principal
                </div>
                {detected.latest_resume ? (
                  <div className="mt-3 text-sm text-slate-600">
                    <p className="font-medium text-ink">{detected.latest_resume.filename}</p>
                    <div className="mt-2">
                      <StatusBadge status={detected.latest_resume.status} />
                    </div>
                    {detected.latest_resume.error_message ? (
                      <p className="mt-2 text-rose-700">{detected.latest_resume.error_message}</p>
                    ) : null}
                  </div>
                ) : (
                  <p className="mt-3 text-sm text-slate-600">Sube un CV para generar este perfil automáticamente.</p>
                )}
              </div>
            </div>

            <div className="rounded-lg border border-line bg-white p-5 shadow-panel">
              <h2 className="font-semibold text-ink">Datos faltantes útiles</h2>
              <p className="mt-2 text-sm text-slate-600">
                No bloquean el flujo. Puedes completarlos para mejorar matching o ayudar a formularios.
              </p>
              <div className="mt-4 grid gap-3 md:grid-cols-2">
                {detected.recommendations.length ? (
                  detected.recommendations.map((item) => (
                    <div key={item.field} className="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm">
                      <p className="font-semibold text-amber-900">{item.message}</p>
                      <p className="mt-1 text-amber-800">{item.reason}</p>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
                    <CheckCircle2 className="h-4 w-4" />
                    El perfil tiene suficientes datos para buscar y rankear vacantes.
                  </div>
                )}
              </div>
            </div>
          </section>

          <section className="mt-6 rounded-lg border border-line bg-white p-5 shadow-panel">
            <h2 className="font-semibold text-ink">Lo que detectó JobPilot AI</h2>
            <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {detected.fields.map((field) => (
                <DetectedFieldCard key={field.key} field={field} />
              ))}
            </div>
          </section>

          <section className="mt-6 rounded-lg border border-line bg-white p-5 shadow-panel">
            <h2 className="font-semibold text-ink">Completar solo faltantes</h2>
            <p className="mt-2 text-sm text-slate-600">
              Estos datos son opcionales y quedan marcados como ingresados por el usuario.
            </p>
            {editableMissing.length ? (
              <form onSubmit={submit} className="mt-4">
                <div className="grid gap-4 md:grid-cols-2">
                  {editableMissing.map((field) => {
                    const config = editableFields[field];
                    return (
                      <label key={field} className="block text-sm font-medium text-slate-700">
                        {config.label}
                        <input
                          value={form[field] ?? ""}
                          onChange={(event) => update(field, event.target.value)}
                          type={config.type ?? "text"}
                          placeholder={config.placeholder}
                          className="mt-2 w-full rounded-lg border border-line px-3 py-2 outline-none focus:border-brand"
                        />
                      </label>
                    );
                  })}
                  {editableMissing.includes("salary_expectation") ? (
                    <label className="block text-sm font-medium text-slate-700">
                      Moneda
                      <input
                        value={form.salary_currency ?? ""}
                        onChange={(event) => update("salary_currency", event.target.value)}
                        placeholder="USD"
                        className="mt-2 w-full rounded-lg border border-line px-3 py-2 outline-none focus:border-brand"
                      />
                    </label>
                  ) : null}
                </div>
                <div className="mt-5 flex justify-end">
                  <button
                    type="submit"
                    disabled={saving}
                    className="inline-flex items-center gap-2 rounded-lg bg-brand px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
                  >
                    {saving ? <Loader2 className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
                    Guardar faltantes
                  </button>
                </div>
              </form>
            ) : (
              <p className="mt-4 rounded-lg bg-emerald-50 p-3 text-sm text-emerald-800">
                No hay campos faltantes editables en este momento.
              </p>
            )}
          </section>
        </>
      ) : (
        <Notice tone="error" text={error ?? "No se pudo cargar el perfil detectado"} />
      )}
    </div>
  );
}

function DetectedFieldCard({ field }: { field: DetectedProfileField }) {
  return (
    <article className="rounded-lg border border-line p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-ink">{field.label}</h3>
          <p className="mt-1 text-xs text-slate-500">{field.useful_for}</p>
        </div>
        <SourceBadge field={field} />
      </div>
      <p className="mt-3 min-h-10 whitespace-pre-line text-sm leading-6 text-slate-700">{formatValue(field.value)}</p>
      {field.needs_confirmation ? (
        <p className="mt-2 text-xs font-medium text-slate-500">Pendiente de confirmación</p>
      ) : null}
    </article>
  );
}

function SourceBadge({ field }: { field: DetectedProfileField }) {
  const styles: Record<string, string> = {
    detected: "border-teal-200 bg-teal-50 text-teal-800",
    inferred: "border-indigo-200 bg-indigo-50 text-indigo-800",
    user_input: "border-slate-200 bg-slate-100 text-slate-700",
    missing: "border-amber-200 bg-amber-50 text-amber-800",
    pending_confirmation: "border-sky-200 bg-sky-50 text-sky-800"
  };
  const labels: Record<string, string> = {
    detected: "Detectado",
    inferred: "Inferido",
    user_input: "Usuario",
    missing: "Faltante",
    pending_confirmation: "Pendiente"
  };
  return (
    <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold ${styles[field.status]}`}>
      {labels[field.status]}
    </span>
  );
}

function Notice({ tone, text }: { tone: "error" | "success"; text: string }) {
  const style = tone === "error" ? "bg-rose-50 text-rose-700" : "bg-emerald-50 text-emerald-700";
  return (
    <div className={`mb-4 flex items-start gap-2 rounded-lg p-3 text-sm ${style}`}>
      <AlertCircle className="mt-0.5 h-4 w-4" />
      <span>{text}</span>
    </div>
  );
}

function formatValue(value: DetectedProfileField["value"]): string {
  if (Array.isArray(value)) {
    return value.length ? value.join(", ") : "No detectado";
  }
  if (value === null || value === undefined || value === "") {
    return "No detectado";
  }
  return String(value);
}

function buildInitialForm(data: DetectedProfile): MissingForm {
  const form: MissingForm = {};
  for (const field of data.missing_fields) {
    if (field in editableFields) {
      form[field] = "";
    }
  }
  if (data.missing_fields.includes("salary_expectation")) {
    form.salary_currency = data.profile.salary_currency ?? "USD";
  }
  return form;
}
