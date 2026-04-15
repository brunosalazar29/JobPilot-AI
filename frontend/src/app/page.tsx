import { ArrowRight, CheckCircle2, FileText, Search, ShieldCheck, WandSparkles } from "lucide-react";
import Link from "next/link";

const features = [
  { title: "CV estructurado", text: "Carga PDF o DOCX y convierte el contenido en datos útiles.", icon: FileText },
  { title: "Matching explicable", text: "Prioriza vacantes por skills, seniority, idioma, ubicación y salario.", icon: Search },
  { title: "Documentos listos", text: "Genera respuestas, resúmenes y cover letters editables.", icon: WandSparkles },
  { title: "Revisión manual", text: "Prepara formularios sin enviar postulaciones sin aprobación.", icon: ShieldCheck }
];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-mist">
      <section className="mx-auto flex min-h-screen max-w-7xl flex-col px-5 py-6">
        <nav className="flex items-center justify-between">
          <div className="flex items-center gap-3 font-semibold text-ink">
            <span className="grid h-10 w-10 place-items-center rounded-lg bg-brand text-white">JP</span>
            <span>JobPilot AI</span>
          </div>
          <div className="flex gap-2">
            <Link className="rounded-lg border border-line bg-white px-4 py-2 text-sm font-medium text-ink" href="/login">
              Entrar
            </Link>
            <Link className="rounded-lg bg-brand px-4 py-2 text-sm font-medium text-white" href="/register">
              Crear cuenta
            </Link>
          </div>
        </nav>

        <div className="grid flex-1 items-center gap-10 py-12 lg:grid-cols-[1.05fr_0.95fr]">
          <div>
            <p className="inline-flex items-center gap-2 rounded-full border border-teal-200 bg-teal-50 px-3 py-1 text-sm font-medium text-brand">
              <CheckCircle2 className="h-4 w-4" />
              Plataforma semi-automática para postulaciones
            </p>
            <h1 className="mt-6 max-w-3xl text-5xl font-semibold tracking-normal text-ink sm:text-6xl">
              JobPilot AI
            </h1>
            <p className="mt-5 max-w-2xl text-lg leading-8 text-slate-600">
              Centraliza CV, búsqueda de empleos, ranking de compatibilidad, generación de documentos y preparación de
              formularios con aprobación final del usuario.
            </p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link
                href="/dashboard"
                className="inline-flex items-center gap-2 rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-white"
              >
                Abrir dashboard
                <ArrowRight className="h-4 w-4" />
              </Link>
              <Link
                href="/login"
                className="inline-flex items-center gap-2 rounded-lg border border-line bg-white px-5 py-3 text-sm font-semibold text-ink"
              >
                Iniciar sesión
              </Link>
            </div>
          </div>

          <div className="rounded-lg border border-line bg-white p-4 shadow-panel">
            <div className="rounded-lg bg-slate-950 p-5 text-white">
              <div className="flex items-center justify-between border-b border-white/10 pb-4">
                <div>
                  <p className="text-sm text-slate-300">Pipeline actual</p>
                  <p className="mt-1 text-2xl font-semibold">18 vacantes evaluadas</p>
                </div>
                <span className="rounded-full bg-emerald-400/15 px-3 py-1 text-sm text-emerald-200">6 listas</span>
              </div>
              <div className="mt-5 space-y-3">
                {["Parseo CV", "Matching", "Cover letter", "Formulario preparado"].map((item, index) => (
                  <div key={item} className="flex items-center justify-between rounded-lg bg-white/6 p-3">
                    <span className="text-sm">{item}</span>
                    <span className="text-sm text-slate-300">{index === 3 ? "review" : "done"}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-4 pb-8 md:grid-cols-2 lg:grid-cols-4">
          {features.map((feature) => {
            const Icon = feature.icon;
            return (
              <div key={feature.title} className="rounded-lg border border-line bg-white p-5">
                <Icon className="h-5 w-5 text-brand" />
                <h2 className="mt-4 font-semibold text-ink">{feature.title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-600">{feature.text}</p>
              </div>
            );
          })}
        </div>
      </section>
    </main>
  );
}
