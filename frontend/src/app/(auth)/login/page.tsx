"use client";

import { ArrowRight, Loader2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { apiFetch, setToken } from "@/lib/api";

type TokenResponse = {
  access_token: string;
  token_type: string;
};

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("demo@jobpilot.ai");
  const [password, setPassword] = useState("DemoPass123");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const response = await apiFetch<TokenResponse>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email, password })
      });
      setToken(response.access_token);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="grid min-h-screen place-items-center bg-mist px-4">
      <form onSubmit={submit} className="w-full max-w-md rounded-lg border border-line bg-white p-6 shadow-panel">
        <div className="mb-6">
          <Link href="/" className="text-sm font-semibold text-brand">
            JobPilot AI
          </Link>
          <h1 className="mt-3 text-2xl font-semibold text-ink">Iniciar sesión</h1>
          <p className="mt-2 text-sm text-slate-600">Usa tus credenciales para entrar al dashboard.</p>
        </div>

        <label className="block text-sm font-medium text-slate-700">
          Email
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-2 w-full rounded-lg border border-line px-3 py-2 outline-none focus:border-brand"
            type="email"
            required
          />
        </label>
        <label className="mt-4 block text-sm font-medium text-slate-700">
          Contraseña
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-2 w-full rounded-lg border border-line px-3 py-2 outline-none focus:border-brand"
            type="password"
            required
          />
        </label>

        {error ? <p className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-700">{error}</p> : null}

        <button
          type="submit"
          disabled={loading}
          className="mt-6 inline-flex w-full items-center justify-center gap-2 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
        >
          {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <ArrowRight className="h-4 w-4" />}
          Entrar
        </button>
        <p className="mt-4 text-center text-sm text-slate-600">
          ¿No tienes cuenta?{" "}
          <Link href="/register" className="font-semibold text-brand">
            Crear cuenta
          </Link>
        </p>
      </form>
    </main>
  );
}
