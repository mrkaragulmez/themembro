// frontend/src/app/page.tsx
// Faz 1 — Ana sayfa (placeholder)

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <div className="text-center">
        <h1 className="text-4xl font-bold tracking-tight">Membro</h1>
        <p className="mt-2 text-lg text-gray-500">Agentic AI Platform</p>
      </div>

      <div className="flex gap-4">
        <a
          href="/login"
          className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-semibold text-white shadow-sm hover:bg-indigo-500 transition-colors"
        >
          Giriş Yap
        </a>
        <a
          href="/register"
          className="rounded-lg border border-gray-300 bg-white px-5 py-2.5 text-sm font-semibold text-gray-700 shadow-sm hover:bg-gray-50 transition-colors"
        >
          Kayıt Ol
        </a>
      </div>
    </main>
  );
}
