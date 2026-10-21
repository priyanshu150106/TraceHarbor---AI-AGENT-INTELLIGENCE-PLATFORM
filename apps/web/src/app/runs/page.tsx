"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchRuns } from "@/lib/api";
import { RunListResponse, RunSummary } from "@/lib/types";

export default function RunsExplorerPage() {
  const [data, setData] = useState<RunListResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const loadRuns = React.useCallback(
    (page = 1, status = statusFilter, search = searchQuery) => {
      setLoading(true);
      setError(null);
      fetchRuns({
        page,
        pageSize: 15,
        status: status !== "all" ? status : undefined,
        search: search.trim() ? search.trim() : undefined,
      })
        .then((res) => {
          setData(res);
          setCurrentPage(res.page);
        })
        .catch((err) => setError(err.message || "Failed to load runs."))
        .finally(() => setLoading(false));
    },
    [statusFilter, searchQuery]
  );

  useEffect(() => {
    loadRuns(1, statusFilter, searchQuery);
  }, [loadRuns, statusFilter, searchQuery]);


  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadRuns(1, statusFilter, searchQuery);
  };

  const copyToClipboard = (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 1500);
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title="Runs Explorer" />

        <main className="p-8 space-y-6 flex-1 overflow-y-auto max-w-6xl w-full mx-auto">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">Runs Explorer</h1>
              <p className="text-xs text-slate-400 mt-1">
                Inspect, filter, and drill into historical AI agent executions.
              </p>
            </div>
            <button
              onClick={() => loadRuns(currentPage, statusFilter, searchQuery)}
              disabled={loading}
              className="px-3 py-1.5 text-xs rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700 flex items-center space-x-1.5 self-start disabled:opacity-50"
            >
              <svg className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Refresh</span>
            </button>
          </div>

          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/60 border border-slate-800 p-3 rounded-lg">
            <form onSubmit={handleSearchSubmit} className="flex items-center space-x-2 w-full sm:w-80">
              <div className="relative w-full">
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search agent name..."
                  className="w-full bg-slate-950 border border-slate-800 rounded-md px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
                />
              </div>
              <button
                type="submit"
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-xs rounded-md border border-slate-700 text-slate-300 transition shrink-0"
              >
                Search
              </button>
            </form>

            <div className="flex items-center space-x-2 self-end sm:self-auto">
              <span className="text-xs text-slate-400">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-slate-950 border border-slate-800 rounded-md px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500/50"
              >
                <option value="all">All Statuses</option>
                <option value="completed">Completed</option>
                <option value="error">Error</option>
                <option value="running">Running</option>
              </select>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-4 text-xs text-rose-300">
              <p className="font-semibold text-rose-200">Error loading runs</p>
              <p>{error}</p>
            </div>
          )}

          {/* Runs Table */}
          <div className="rounded-lg border border-slate-800 bg-slate-900/50 overflow-hidden shadow-sm">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-slate-800 bg-slate-900/80 text-slate-400 font-medium">
                <tr>
                  <th className="py-3 px-4">Run ID</th>
                  <th className="py-3 px-4">Agent Name</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Started At</th>
                  <th className="py-3 px-4">Duration</th>
                  <th className="py-3 px-4">Tokens</th>
                  <th className="py-3 px-4">Est. Cost</th>
                  <th className="py-3 px-4 text-right">Details</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {loading ? (
                  <tr>
                    <td colSpan={8} className="py-8 text-center text-slate-500">
                      <div className="flex items-center justify-center space-x-2">
                        <svg className="w-4 h-4 animate-spin text-emerald-500" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"></path>
                        </svg>
                        <span>Loading execution runs...</span>
                      </div>
                    </td>
                  </tr>
                ) : !data || data.items.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="py-12 text-center text-slate-400 space-y-2">
                      <p className="text-sm font-medium text-slate-300">No runs found matching current filter</p>
                      <p className="text-xs text-slate-500">
                        Try clearing search terms or run <code className="text-slate-400">python demo-agents/support_agent.py</code> to emit a new trace.
                      </p>
                    </td>
                  </tr>
                ) : (
                  data.items.map((run: RunSummary) => (
                    <tr
                      key={run.id}
                      className="hover:bg-slate-800/40 cursor-pointer transition group"
                      onClick={() => (window.location.href = `/runs/${run.id}`)}
                    >
                      <td className="py-3 px-4 font-mono text-slate-400 flex items-center space-x-1.5">
                        <span>{run.id.slice(0, 8)}...</span>
                        <button
                          onClick={(e) => copyToClipboard(run.id, e)}
                          title="Copy Full UUID"
                          className="text-slate-600 hover:text-slate-300 transition opacity-0 group-hover:opacity-100"
                        >
                          {copiedId === run.id ? (
                            <span className="text-[10px] text-emerald-400 font-sans">Copied!</span>
                          ) : (
                            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                            </svg>
                          )}
                        </button>
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
                        {new Date(run.started_at).toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-slate-300 font-mono">
                        {run.duration_ms !== null ? `${run.duration_ms}ms` : "-"}
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-mono">
                        {run.total_tokens.toLocaleString()}
                      </td>
                      <td className="py-3 px-4 text-slate-400 font-mono">
                        ${Number(run.total_cost_usd).toFixed(5)}
                      </td>
                      <td className="py-3 px-4 text-right">
                        <Link
                          href={`/runs/${run.id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="text-emerald-400 hover:text-emerald-300 font-medium transition"
                        >
                          View Trace →
                        </Link>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>

            {/* Pagination Controls */}
            {data && data.total_pages > 1 && (
              <div className="border-t border-slate-800 bg-slate-900/60 px-4 py-3 flex items-center justify-between text-xs text-slate-400">
                <span>
                  Showing page <span className="text-white font-medium">{data.page}</span> of{" "}
                  <span className="text-white font-medium">{data.total_pages}</span> ({data.total} total runs)
                </span>
                <div className="flex items-center space-x-2">
                  <button
                    disabled={currentPage <= 1 || loading}
                    onClick={() => loadRuns(currentPage - 1)}
                    className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 disabled:opacity-40 transition"
                  >
                    Previous
                  </button>
                  <button
                    disabled={currentPage >= data.total_pages || loading}
                    onClick={() => loadRuns(currentPage + 1)}
                    className="px-2.5 py-1 rounded bg-slate-800 border border-slate-700 text-slate-300 hover:bg-slate-700 disabled:opacity-40 transition"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
