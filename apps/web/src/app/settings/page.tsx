"use client";

import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchHealth, getStoredApiKey, setStoredApiKey, clearStoredApiKey } from "@/lib/api";
import { HealthStatus } from "@/lib/types";

export default function SettingsPage() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [apiKeyInput, setApiKeyInput] = useState("");
  const [savedKey, setSavedKey] = useState<string | null>(null);
  const [savedMessage, setSavedMessage] = useState<string | null>(null);

  useEffect(() => {
    fetchHealth()
      .then((data) => setHealth(data))
      .catch(() => setHealth(null))
      .finally(() => setLoading(false));

    const existing = getStoredApiKey();
    if (existing) {
      setSavedKey(existing);
      setApiKeyInput(existing);
    }
  }, []);

  const handleSaveKey = (e: React.FormEvent) => {
    e.preventDefault();
    setStoredApiKey(apiKeyInput);
    setSavedKey(apiKeyInput.trim() || null);
    setSavedMessage("API key saved to local session.");
    setTimeout(() => setSavedMessage(null), 3000);
  };

  const handleClearKey = () => {
    clearStoredApiKey();
    setApiKeyInput("");
    setSavedKey(null);
    setSavedMessage("API key cleared.");
    setTimeout(() => setSavedMessage(null), 3000);
  };

  const apiBaseUrl =
    process.env.NEXT_PUBLIC_API_BASE_URL ||
    process.env.NEXT_PUBLIC_API_URL ||
    "http://localhost:8000";

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
              Configuration, endpoint bindings, authentication, and platform architecture telemetry.
            </p>
          </div>

          {/* Configuration Cards */}
          <div className="space-y-4">
            {/* API Key Configuration */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Project API Key Authentication</h3>
                  <p className="text-xs text-slate-400">
                    Propagates via <code className="text-slate-300">X-API-Key</code> header to authenticate dashboard requests against production API instances.
                  </p>
                </div>
                <span className={`px-2 py-0.5 rounded text-[10px] font-mono border ${savedKey ? "bg-emerald-950/60 text-emerald-400 border-emerald-800" : "bg-slate-800 text-slate-400 border-slate-700"}`}>
                  {savedKey ? "Key Configured" : "Unset (Dev Mode)"}
                </span>
              </div>

              <form onSubmit={handleSaveKey} className="space-y-2">
                <div className="flex gap-2">
                  <input
                    type="password"
                    placeholder="th_live_..."
                    value={apiKeyInput}
                    onChange={(e) => setApiKeyInput(e.target.value)}
                    className="flex-1 rounded bg-slate-950 border border-slate-800 px-3 py-2 text-xs font-mono text-slate-200 placeholder:text-slate-600 focus:outline-none focus:border-indigo-500"
                  />
                  <button
                    type="submit"
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-medium transition-colors"
                  >
                    Save Key
                  </button>
                  {savedKey && (
                    <button
                      type="button"
                      onClick={handleClearKey}
                      className="px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded text-xs transition-colors"
                    >
                      Clear
                    </button>
                  )}
                </div>
                {savedMessage && (
                  <p className="text-[11px] text-emerald-400 font-medium">{savedMessage}</p>
                )}
                <p className="text-[11px] text-slate-500">
                  In development (<code className="text-slate-400">DEBUG=true</code>), unauthenticated requests fall back to the primary project. In staging/production, requests require this key.
                </p>
              </form>
            </div>

            {/* Backend Endpoint Config */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-white">Backend API Ingestion URL</h3>
                  <p className="text-xs text-slate-400">
                    The HTTP URL used by the web client and Python SDK to ingest trace events and query telemetry.
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
                Configured via <code className="text-slate-400">NEXT_PUBLIC_API_BASE_URL</code> in frontend environment variables.
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
                  <span className="text-[10px] uppercase text-slate-500 block">Platform Release</span>
                  <span className="text-xs font-mono text-slate-300">
                    {health ? `${health.version} (Phase 8 RC)` : "0.1.0-rc1"}
                  </span>
                </div>
                <div className="bg-slate-950 p-3 rounded border border-slate-800/80">
                  <span className="text-[10px] uppercase text-slate-500 block">Python SDK Version</span>
                  <span className="text-xs font-mono text-slate-300">
                    0.1.0 (Editable / Monorepo)
                  </span>
                </div>
              </div>
            </div>

            {/* Platform Capabilities & Architecture */}
            <div className="rounded-xl border border-slate-800 bg-slate-900/30 p-5 space-y-3 text-xs text-slate-400">
              <div className="flex items-center justify-between">
                <h3 className="text-sm font-semibold text-white">Implemented Platform Capabilities</h3>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-indigo-950/80 text-indigo-300 border border-indigo-800">
                  Phase 8 Release Candidate
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-slate-300">
                <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800/60">
                  <strong className="text-white block mb-0.5">Telemetry & Tracing (Phases 1-2)</strong>
                  <span className="text-[11px] text-slate-400">Asynchronous background worker, parent-child span hierarchy, waterfall latency visualizer.</span>
                </div>
                <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800/60">
                  <strong className="text-white block mb-0.5">Evaluation & Regression (Phase 3)</strong>
                  <span className="text-[11px] text-slate-400">Automated dataset evaluations, LLM judges, golden test suites, side-by-side agent comparison.</span>
                </div>
                <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800/60">
                  <strong className="text-white block mb-0.5">Safety & Red-Teaming (Phase 5)</strong>
                  <span className="text-[11px] text-slate-400">Jailbreak resistance, prompt injection benchmarks, secret leakage canaries, safety boundary timeouts.</span>
                </div>
                <div className="p-2.5 rounded bg-slate-950/70 border border-slate-800/60">
                  <strong className="text-white block mb-0.5">Failure Intelligence (Phase 6)</strong>
                  <span className="text-[11px] text-slate-400">Redaction sanitization, semantic vector clustering, pgvector similarity search, triage investigation workflow.</span>
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
