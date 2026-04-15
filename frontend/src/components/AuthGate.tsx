"use client";

import { Loader2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { apiFetch, clearToken, getToken } from "@/lib/api";

export function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [authorized, setAuthorized] = useState(false);

  useEffect(() => {
    async function checkSession() {
      const token = getToken();
      if (!token) {
        router.replace("/login");
        return;
      }

      try {
        await apiFetch("/auth/me");
        setAuthorized(true);
      } catch {
        clearToken();
        router.replace("/login");
      }
    }

    void checkSession();
  }, [router]);

  if (!authorized) {
    return (
      <main className="grid min-h-screen place-items-center bg-mist">
        <div className="flex items-center gap-2 text-sm text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" />
          Verificando sesión...
        </div>
      </main>
    );
  }

  return <>{children}</>;
}
