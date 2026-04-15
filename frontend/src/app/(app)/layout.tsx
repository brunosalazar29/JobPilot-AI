import { AuthGate } from "@/components/AuthGate";
import { AppShell } from "@/components/AppShell";

export default function ProtectedLayout({ children }: { children: React.ReactNode }) {
  return (
    <AuthGate>
      <AppShell>{children}</AppShell>
    </AuthGate>
  );
}
