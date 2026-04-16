import { API_URL } from "@/lib/api";
import type { Application, TaskRun } from "@/types";

export type ConsoleEntry = {
  key: string;
  timestamp: string;
  source: "task" | "application";
  title: string;
  detail: string;
  level: string;
};

const statusLabels: Record<string, string> = {
  pending: "Pendiente",
  found: "Vacante encontrada",
  matched: "Compatible",
  queued: "En cola",
  preparing: "Preparando formulario",
  applying: "Intentando postular",
  running: "En proceso",
  prepared: "Preparado",
  completed: "Completado",
  parsed: "Analizado",
  uploaded: "Cargado",
  ready_for_review: "Lista para revisar",
  applied: "Postulación enviada",
  failed: "Falló",
  rejected: "Rechazada",
  needs_manual_action: "Requiere revisión manual",
  paused: "Pausado",
  cancelled: "Cancelado",
  stopping: "Deteniendo",
  stopped: "Detenido",
  idle: "Sin actividad"
};

const statusDescriptions: Record<string, string> = {
  found: "La vacante fue encontrada y está pendiente de evaluar.",
  matched: "La vacante es compatible con tu perfil.",
  queued: "La vacante quedó en cola para intentar la postulación.",
  preparing: "El sistema está abriendo el formulario real.",
  applying: "El sistema está llenando datos y subiendo tu CV.",
  ready_for_review: "El formulario quedó preparado para revisión y envío final.",
  applied: "La postulación fue enviada.",
  failed: "La automatización falló y necesita reintento o descarte.",
  needs_manual_action: "La automatización no pudo continuar sola y necesita tu intervención.",
  paused: "La cola está pausada.",
  cancelled: "La vacante fue cancelada y no se seguirá procesando."
};

const taskLabels: Record<string, string> = {
  cv_pipeline: "Analizando CV y preparando postulaciones",
  parse_resume: "Analizando CV y detectando perfil",
  search_jobs: "Buscando vacantes",
  run_matching: "Evaluando compatibilidad con vacantes",
  prepare_application_form: "Preparando formulario de postulación",
  auto_apply: "Intentando postular automáticamente",
  notify_user: "Notificando resultados"
};

const taskDescriptions: Record<string, string> = {
  cv_pipeline: "Analiza tu CV, detecta tu perfil, busca vacantes, calcula compatibilidad y arma la cola.",
  parse_resume: "Lee tu CV y actualiza tu perfil detectado para futuras busquedas.",
  search_jobs: "Busca vacantes relacionadas con tu perfil en fuentes configuradas.",
  run_matching: "Compara tu CV con las vacantes encontradas.",
  prepare_application_form: "Abre el portal de empleo, llena campos comunes y adjunta tu CV.",
  auto_apply: "Intenta completar la postulación en segundo plano.",
  notify_user: "Prepara el resumen de resultados para que sepas qué pasó."
};

const fieldLabels: Record<string, string> = {
  full_name: "nombre completo",
  first_name: "nombre",
  last_name: "apellido",
  email: "correo",
  phone: "teléfono",
  location: "ubicación",
  linkedin: "LinkedIn",
  github: "GitHub",
  portfolio: "portafolio",
  resume: "CV"
};

const absoluteFormatter = new Intl.DateTimeFormat("es-PE", {
  dateStyle: "short",
  timeStyle: "short"
});

const relativeFormatter = new Intl.RelativeTimeFormat("es", { numeric: "auto" });

export function getStatusLabel(status: string | null | undefined): string {
  if (!status) {
    return "Sin estado";
  }
  return statusLabels[status] ?? status.replaceAll("_", " ");
}

export function getStatusDescription(status: string | null | undefined): string {
  if (!status) {
    return "Sin actividad registrada.";
  }
  return statusDescriptions[status] ?? "Estado operativo actualizado.";
}

export function getTaskLabel(taskName: string | null | undefined): string {
  if (!taskName) {
    return "Proceso";
  }
  return taskLabels[taskName] ?? taskName.replaceAll("_", " ");
}

export function getTaskDescription(taskName: string | null | undefined): string {
  if (!taskName) {
    return "Proceso en segundo plano.";
  }
  return taskDescriptions[taskName] ?? "Proceso interno en segundo plano.";
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  return absoluteFormatter.format(new Date(value));
}

export function formatRelativeTime(value: string | null | undefined): string {
  if (!value) {
    return "-";
  }
  const target = new Date(value).getTime();
  const diffMs = target - Date.now();
  const diffSeconds = Math.round(diffMs / 1000);
  const absSeconds = Math.abs(diffSeconds);

  if (absSeconds < 10) {
    return "Hace unos segundos";
  }
  if (absSeconds < 60) {
    return relativeFormatter.format(diffSeconds, "second");
  }
  const diffMinutes = Math.round(diffSeconds / 60);
  if (Math.abs(diffMinutes) < 60) {
    return relativeFormatter.format(diffMinutes, "minute");
  }
  const diffHours = Math.round(diffMinutes / 60);
  if (Math.abs(diffHours) < 24) {
    return relativeFormatter.format(diffHours, "hour");
  }
  const diffDays = Math.round(diffHours / 24);
  return relativeFormatter.format(diffDays, "day");
}

export function formatDuration(start: string | null | undefined, end?: string | null | undefined): string {
  if (!start) {
    return "-";
  }
  const startMs = new Date(start).getTime();
  const endMs = end ? new Date(end).getTime() : Date.now();
  const seconds = Math.max(0, Math.round((endMs - startMs) / 1000));
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (minutes === 0) {
    return `${remainingSeconds}s`;
  }
  if (minutes < 60) {
    return `${minutes}m ${remainingSeconds}s`;
  }
  const hours = Math.floor(minutes / 60);
  return `${hours}h ${minutes % 60}m`;
}

export function getDomainLabel(url: string | null | undefined): string {
  if (!url) {
    return "Sin enlace";
  }
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return url;
  }
}

export function getApplicationCurrentMessage(application: Application): string {
  const translatedLog = translateLastLog(application.logs);
  if (translatedLog) {
    return translatedLog;
  }
  if (application.errors) {
    return explainError(application.errors, application.status);
  }
  return getStatusDescription(application.status);
}

export function getTaskCurrentMessage(task: TaskRun): string {
  const translatedLog = translateLastLog(task.logs);
  if (translatedLog) {
    return translatedLog;
  }
  if (task.error_message) {
    return explainError(task.error_message, task.status);
  }
  return getTaskDescription(task.task_name);
}

export function getManualActionGuidance(application: Application): string | null {
  if (!["needs_manual_action", "ready_for_review", "failed"].includes(application.status)) {
    return null;
  }
  if (application.errors) {
    return explainError(application.errors, application.status);
  }
  const translatedLog = translateLastLog(application.logs);
  if (translatedLog) {
    return translatedLog;
  }
  return "Abre la vacante y completa el paso que el portal no permitió automatizar.";
}

export function getEvidenceUrl(path: unknown): string | null {
  if (typeof path !== "string" || !path.trim()) {
    return null;
  }
  if (path.startsWith("/app/storage/")) {
    return `${API_URL}${path.replace("/app/storage", "/storage")}`;
  }
  if (path.startsWith("/storage/")) {
    return `${API_URL}${path}`;
  }
  return path;
}

export function getLatestEvidence(application: Application): { url: string | null; label: string | null } {
  const latest = [...application.document_refs].reverse().find((entry) => entry?.type === "automation_screenshot");
  if (!latest) {
    return { url: null, label: null };
  }
  const url = getEvidenceUrl(latest.path);
  const domain = typeof latest.domain === "string" ? latest.domain : null;
  return {
    url,
    label: domain ? `Evidencia del intento en ${domain}` : "Evidencia del intento"
  };
}

export function getLatestTimestamp(items: Array<Record<string, unknown>>): string | null {
  const timestamps = items
    .map((item) => (typeof item.timestamp === "string" ? item.timestamp : null))
    .filter((value): value is string => Boolean(value))
    .sort((left, right) => right.localeCompare(left));
  return timestamps[0] ?? null;
}

export function buildConsoleEntries(tasks: TaskRun[], applications: Application[]): ConsoleEntry[] {
  const taskEntries = tasks.flatMap((task) =>
    (task.logs ?? [])
      .filter((log) => typeof log.timestamp === "string" && typeof log.message === "string")
      .map((log, index) => ({
        key: `task-${task.id}-${index}`,
        timestamp: String(log.timestamp),
        source: "task" as const,
        title: getTaskLabel(task.task_name),
        detail: translateLogMessage(String(log.message)) ?? String(log.message),
        level: typeof log.level === "string" ? log.level : "info"
      }))
  );

  const applicationEntries = applications.flatMap((application) =>
    (application.logs ?? [])
      .filter((log) => typeof log.timestamp === "string" && typeof log.message === "string")
      .map((log, index) => ({
        key: `application-${application.id}-${index}`,
        timestamp: String(log.timestamp),
        source: "application" as const,
        title: `${application.company} · ${application.position}`,
        detail: translateLogMessage(String(log.message)) ?? String(log.message),
        level: typeof log.level === "string" ? log.level : "info"
      }))
  );

  return [...taskEntries, ...applicationEntries]
    .sort((left, right) => right.timestamp.localeCompare(left.timestamp))
    .slice(0, 20);
}

export function summarizeTaskResult(task: TaskRun): string | null {
  if (task.task_name !== "cv_pipeline") {
    return null;
  }
  const jobsCollected = asNumber(task.result.jobs_collected);
  const matchesCreated = asNumber(task.result.matches_created);
  const queueItemsCreated = asNumber(task.result.queue_items_created);
  const autoApplyTasks = asNumber(task.result.auto_apply_tasks);
  return `${jobsCollected} vacantes encontradas, ${matchesCreated} compatibles, ${queueItemsCreated} en cola, ${autoApplyTasks} intentos iniciados.`;
}

export function translateLogMessage(message: string | null | undefined): string | null {
  if (!message) {
    return null;
  }

  const directMap: Record<string, string> = {
    "Started resume parsing": "Leyendo el CV para actualizar tu perfil detectado.",
    "parse_cv started": "Analizando CV y extrayendo experiencia, skills y datos de contacto.",
    "parse_cv skipped: using stored parsed CV": "Usando el CV ya analizado para iniciar la busqueda.",
    "infer_profile started": "Infiriendo perfil profesional desde tu CV.",
    "collect_jobs started": "Buscando vacantes relacionadas con tu perfil.",
    "collect_jobs skipped: no real job sources configured": "No hay fuentes reales configuradas para buscar vacantes.",
    "match_jobs started": "Evaluando compatibilidad con las vacantes encontradas.",
    "create_queue_items started": "Creando la cola de postulaciones compatibles.",
    "auto_apply started": "Iniciando intentos automáticos de postulación.",
    "Preparing web application form": "Preparando el formulario de postulación.",
    "Queue item created from CV pipeline": "Vacante agregada a la cola por compatibilidad.",
    "Queue item ready for auto-apply": "Vacante lista para intentar la postulación automática.",
    "Uploading CV": "Subiendo tu CV al formulario.",
    "Attached resume file": "CV cargado en el formulario.",
    "Blocked by captcha challenge": "El portal pidió captcha y requiere tu intervención.",
    "Waiting manual final submission": "El formulario quedó listo para revisión y envío final.",
    "Reached external application form": "Se llegó al formulario real de postulación.",
    "Real application form prepared": "El formulario real quedó preparado.",
    "Final submission was not attempted automatically": "El sistema dejó el formulario listo, pero no envió la postulación automáticamente.",
    "Real application form was not detected": "No se encontro un formulario real de postulacion en el enlace abierto.",
    "Missing job URL": "La vacante no tiene un enlace directo para continuar.",
    "Search run stopped by user": "La busqueda fue detenida por el usuario."
  };

  if (message in directMap) {
    return directMap[message];
  }

  const applyingMatch = message.match(/^Applying to (.+) at (.+)$/);
  if (applyingMatch) {
    return `Intentando postular para ${applyingMatch[1]} en ${applyingMatch[2]}.`;
  }

  const preparingCompanyMatch = message.match(/^Preparing application for (.+)$/);
  if (preparingCompanyMatch) {
    return `Preparando la postulación para ${preparingCompanyMatch[1]}.`;
  }

  const preparingDomainMatch = message.match(/^Preparing application for domain (.+)$/);
  if (preparingDomainMatch) {
    return `Abriendo el portal ${preparingDomainMatch[1]}.`;
  }

  const openMatch = message.match(/^Opening (.+)$/);
  if (openMatch) {
    return "Abriendo la vacante y cargando el portal de postulación.";
  }

  const filledMatch = message.match(/^Filled ([a-z_]+)$/i);
  if (filledMatch) {
    const field = fieldLabels[filledMatch[1].toLowerCase()] ?? filledMatch[1];
    return `Completando ${field} en el formulario.`;
  }

  const attemptStatusMatch = message.match(/^Application attempt finished with status (.+)$/);
  if (attemptStatusMatch) {
    return `Intento finalizado con estado: ${getStatusLabel(attemptStatusMatch[1])}.`;
  }

  return message;
}

function translateLastLog(logs: Array<Record<string, unknown>>): string | null {
  const last = [...logs].reverse().find((log) => typeof log.message === "string");
  if (!last) {
    return null;
  }
  return translateLogMessage(String(last.message));
}

function explainError(error: string, status?: string): string {
  const normalized = error.toLowerCase();
  if (normalized.includes("captcha")) {
    return "El portal pidió captcha. Abre la vacante, resuélvelo y continúa desde allí.";
  }
  if (normalized.includes("final submission was not attempted automatically")) {
    return "El formulario quedó preparado, pero la postulación final necesita revisión y envío manual.";
  }
  if (normalized.includes("missing job url")) {
    return "La vacante no tiene enlace directo. Necesitas abrirla manualmente o descartarla.";
  }
  if (normalized.includes("no application button found")) {
    return "No se encontró el botón para continuar al formulario real desde la vacante.";
  }
  if (normalized.includes("real application form was not detected")) {
    return "Se abrió el portal, pero no se detectó el formulario real de postulación.";
  }
  if (normalized.includes("external application portal is not supported")) {
    return "El portal real todavía no está soportado para completar la postulación automáticamente.";
  }
  if (normalized.includes("timed out")) {
    return "El portal tardó demasiado en responder y el intento quedó incompleto.";
  }
  if (status === "failed") {
    return "El intento falló. Revisa la evidencia y vuelve a intentarlo.";
  }
  return error;
}

function asNumber(value: unknown): number {
  return typeof value === "number" ? value : 0;
}
