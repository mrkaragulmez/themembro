/**
 * frontend/src/app/(auth)/layout.tsx
 * Faz 6 — Auth route group layout (sidebar/topbar yok)
 */

export default function AuthLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-surface-50 flex items-center justify-center p-4">
      {children}
    </div>
  );
}
