"use client";

import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchHealth } from "@/lib/api";
import { HealthStatus } from "@/lib/types";

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchHealth()
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));
  }, []);

  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title="Platform Settings" />

        <main className="p-8 space-y-6 flex-1 overflow-y-auto max-w-4xl w-full mx-auto">
          {/* Header */}
          <div>
            <h1 className="text-2xl font-bold tracking-tight text-white">System Settings</h1>
            <p className="text-xs text-slate-400 mt-1">
              Configuration, endpoint bindings, and platform architecture telemetry.
            </p>
          </div>

          {/* Configuration Cards */}
          <div className="space-y-4">
            {/* Backend Endpoint Config */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Backend API Ingestion URL</h3>
                  <p className="text-xs text-slate-400">
                    The HTTP URL used by the web client and Python SDK to ingest trace events.
                  </p>
                </div>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                  Read-Only Config
                </span>
              </div>
              <div className="rounded bg-slate-950 border border-slate-800 p-2.5 font-mono text-xs text-emerald-400">
                {apiBaseUrl}
              </div>
              <p className="text-[11px] text-slate-500">
                Configured via <code className="text-slate-400">NEXT_PUBLIC_API_BASE_URL</code> in environment variables.
              </p>
            </div>

            {/* Health & Diagnostic Status */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-3">
              <h3 className="text-sm font-semibold text-white">API Health & Version Diagnostics</h3>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <div className="bg-slate-950 p-3 rounded border border-slate-800/80">
                  <span className="text-[10px] uppercase text-slate-500 block">Service Status</span>
                  <span className={`text-xs font-semibold ${health ? "text-emerald-400" : "text-amber-400"}`}>
                    {loading ? "Checking..." : health ? "Healthy" : "Offline / Unreachable"}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded border border-slate-800/80">
                  <span className="text-[10px] uppercase text-slate-500 block">Platform Version</span>
                  <span className="text-xs font-mono text-slate-300">
                    {health ? health.version : "0.1.0"}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded border border-slate-800/80">
                  <span className="text-[10px] uppercase text-slate-500 block">Python SDK Version</span>
                  <span className="text-xs font-mono text-slate-300">
                    0.1.0 (Local Editable)
                  </span>
                </div>
              </div>
            </div>

            {/* Platform Roadmap Notice */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5 space-y-2 text-xs text-slate-400">
              <h3 className="text-sm font-semibold text-white">Phase Roadmap Notice</h3>
              <p>
                TraceHarbor follows an incremental engineering plan. Phase 2 delivers the core trace waterfall viewer and runs explorer. Future phases will introduce:
              </p>
              <ul className="list-disc pl-5 space-y-1 text-slate-400 mt-2">
                <li><strong className="text-slate-300">Phase 3:</strong> Golden test datasets and automated agent regression comparison.</li>
                <li><strong className="text-slate-300">Phase 4:</strong> Adversarial red-team safety evaluations (prompt injection, jailbreak resistance).</li>
                <li><strong className="text-slate-300">Phase 5:</strong> Intelligence layer with semantic failure clustering via pgvector.</li>
              </ul>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
