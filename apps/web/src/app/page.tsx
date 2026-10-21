"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchAnalyticsOverview } from "@/lib/api";
import { AnalyticsOverview } from "@/lib/types";

export default function OverviewPage() {
  const [data, setData] = useState<AnalyticsOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    setError(null);
    fetchAnalyticsOverview()
      .then((res) => setData(res))
      .catch((err) => setError(err.message || "Failed to load metrics."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

  const hasData = data && data.total_runs > 0;

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title="Platform Overview" />

        <main className="p-8 space-y-8 flex-1 overflow-y-auto max-w-6xl w-full mx-auto">
          {/* Header Banner */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">System Overview</h1>
              <p className="text-xs text-slate-400 mt-1">
                Real-time execution telemetry, error rates, latency percentiles, and token usage.
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={loadData}
                disabled={loading}
                className="px-3 py-1.5 text-xs rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700 flex items-center space-x-1.5 disabled:opacity-50"
              >
                <svg className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                <span>Refresh</span>
              </button>
              <Link
                href="/runs"
                className="px-3.5 py-1.5 text-xs rounded-md bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition shadow-sm"
              >
                Explore Runs →
              </Link>
            </div>
          </div>

          {/* Connection Error Banner */}
          {error && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-300 flex items-start space-x-3">
              <svg className="w-5 h-5 text-amber-400 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
              </svg>
              <div className="space-y-1">
                <p className="font-semibold text-amber-200">Backend Connection Warning</p>
                <p>{error}</p>
                <p className="text-[11px] text-amber-400/80">
                  Tip: Ensure the FastAPI server is running with <code className="bg-amber-950/40 px-1 py-0.5 rounded">python -m uvicorn app.main:app --port 8000</code> in <code className="bg-amber-950/40 px-1 py-0.5 rounded">apps/api</code>.
                </p>
              </div>
            </div>
          )}

          {/* Metric Cards Grid */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-1">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Total Runs</span>
              <p className="text-2xl font-bold text-white">
                {loading ? "..." : data?.total_runs ?? 0}
              </p>
              <span className="text-[10px] text-slate-500 block">All recorded agent executions</span>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-1">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Error Rate</span>
              <p className={`text-2xl font-bold ${data && data.error_rate > 0 ? "text-rose-400" : "text-emerald-400"}`}>
                {loading ? "..." : `${((data?.error_rate ?? 0) * 100).toFixed(1)}%`}
              </p>
              <span className="text-[10px] text-slate-500 block">
                {data ? `${data.failed_runs} failed / ${data.successful_runs} completed` : "No data"}
              </span>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-1">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Avg / P95 Latency</span>
              <p className="text-2xl font-bold text-slate-200">
                {loading ? "..." : `${Math.round(data?.avg_duration_ms ?? 0)}ms`}
              </p>
              <span className="text-[10px] text-slate-400 block">
                P95: {loading ? "..." : `${Math.round(data?.p95_duration_ms ?? 0)}ms`}
              </span>
            </div>

            <div className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-1">
              <span className="text-[11px] font-medium text-slate-400 uppercase tracking-wider">Tokens & Cost</span>
              <p className="text-2xl font-bold text-indigo-400">
                {loading ? "..." : (data?.total_tokens ?? 0).toLocaleString()}
              </p>
              <span className="text-[10px] text-slate-400 block">
                Est. Cost: ${loading ? "..." : (data?.total_cost_usd ?? 0).toFixed(5)}
              </span>
            </div>
          </div>

          {/* Conditional Content: Empty State vs Recent Runs Table */}
          {!loading && !hasData ? (
            <div className="rounded-xl border border-slate-800/80 bg-slate-900/40 p-8 text-center space-y-5">
              <div className="h-12 w-12 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center mx-auto text-slate-400">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                </svg>
              </div>

              <div className="max-w-md mx-auto space-y-2">
                <h3 className="text-base font-semibold text-white">No Agent Runs Recorded Yet</h3>
                <p className="text-xs text-slate-400 leading-relaxed">
                  TraceHarbor displays authentic telemetry emitted by your agents. To see live traces and metrics on this dashboard, execute the deterministic demo agent:
                </p>
              </div>

              <div className="max-w-xl mx-auto rounded-lg border border-slate-800 bg-slate-950 p-4 text-left font-mono text-xs text-slate-300 space-y-2 shadow-inner">
                <p className="text-slate-500 select-none"># 1. Run the deterministic customer support demo agent</p>
                <p className="text-emerald-400 select-all">python demo-agents/support_agent.py</p>
                <p className="text-slate-500 select-none mt-2"># 2. Or test error capture telemetry</p>
                <p className="text-emerald-400 select-all">python demo-agents/support_agent.py --simulate-error</p>
              </div>

              <button
                onClick={loadData}
                className="px-4 py-2 text-xs rounded-md bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition"
              >
                Check for New Traces
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-white uppercase tracking-wider">Recent Executions</h2>
                <Link href="/runs" className="text-xs text-emerald-400 hover:underline">
                  View all runs →
                </Link>
              </div>

              <div className="rounded-lg border border-slate-800 bg-slate-900/50 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-medium">
                    <tr>
                      <th className="py-3 px-4">Run ID</th>
                      <th className="py-3 px-4">Agent Name</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Started At</th>
                      <th className="py-3 px-4">Duration</th>
                      <th className="py-3 px-4">Tokens</th>
                      <th className="py-3 px-4 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {data?.recent_runs.map((run) => (
                      <tr key={run.id} className="hover:bg-slate-800/40 transition">
                        <td className="py-3 px-4 font-mono text-slate-400">
                          {run.id.slice(0, 8)}...
                        </td>
                        <td className="py-3 px-4 font-medium text-white">
                          {run.name || "Untitled Agent"}
                        </td>
                        <td className="py-3 px-4">
                          <span
                            className={`px-2 py-0.5 rounded text-[10px] font-medium border ${
                              run.status === "completed"
                                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                                : run.status === "error"
                                ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                                : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                            }`}
                          >
                            {run.status}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-slate-400">
                          {new Date(run.started_at).toLocaleTimeString()}
                        </td>
                        <td className="py-3 px-4 text-slate-300 font-mono">
                          {run.duration_ms !== null ? `${run.duration_ms}ms` : "-"}
                        </td>
                        <td className="py-3 px-4 text-slate-400 font-mono">
                          {run.total_tokens.toLocaleString()}
                        </td>
                        <td className="py-3 px-4 text-right">
                          <Link
                            href={`/runs/${run.id}`}
                            className="text-emerald-400 hover:text-emerald-300 font-medium transition"
                          >
                            Inspect Trace →
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
