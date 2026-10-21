import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TraceHarbor — Observe. Evaluate. Secure.",
  description:
    "AI Agent Observability, Evaluation, and Security Platform for tracing executions, inspecting LLM calls, evaluating quality, and red-teaming AI safety.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-slate-950 text-slate-100 antialiased selection:bg-emerald-500 selection:text-white">
        {children}
      </body>
    </html>
  );
}
