"use client";

import Link from "next/link";
import React, { useCallback, useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchFailureEvents, fetchFailureOverview, syncFailureEvents } from "@/lib/api";
import { FailureEvent, FailureOverviewMetrics } from "@/lib/types";

export default function FailuresPage() {
  const [metrics, setMetrics] = useState<FailureOverviewMetrics | null>(null);
  const [events, setEvents] = useState<FailureEvent[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [totalPages, setTotalPages] = useState(1);
  const [severityFilter, setSeverityFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [ov, evs] = await Promise.all([
        fetchFailureOverview(),
        fetchFailureEvents({
          page,
          pageSize,
          severity: severityFilter,
          category: categoryFilter,
          search: searchTerm || undefined,
        }),
      ]);
      setMetrics(ov);
      setEvents(evs.items);
      setTotal(evs.total);
      setTotalPages(evs.total_pages);
    } catch (err: any) {
      setError(err.message || "Failed to load failure intelligence data.");
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, severityFilter, categoryFilter, searchTerm]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadData();
  };

  const handleSync = async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
      const res = await syncFailureEvents(true);
      setSyncMessage(`Sync complete: scanned ${res.scanned}, created ${res.created} new events (${res.skipped} skipped).`);
      await loadData();
    } catch (err: any) {
      setError(err.message || "Failure synchronization failed.");
    } finally {
      setSyncing(false);
    }
  };

  const getSeverityBadge = (severity: string) => {
    switch (severity.toLowerCase()) {
      case "critical":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-500" />
            CRITICAL
          </span>
        );
      case "high":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            HIGH
          </span>
        );
      case "medium":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-500" />
            MEDIUM
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-slate-500/10 text-slate-400 border border-slate-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-500" />
            LOW
          </span>
        );
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 antialiased overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">Failure Intelligence</h1>
                <span className="px-2 py-0.5 text-xs font-semibold rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  Phase 6
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-1">
                Normalized failure feed, semantic clustering, and root-cause evidence tracking with PostgreSQL pgvector.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/failures/clusters"
                className="px-3.5 py-2 text-sm font-medium rounded-lg bg-slate-900 border border-slate-700 text-slate-200 hover:bg-slate-800 transition"
              >
                View Clusters ({metrics?.total_clusters || 0})
              </Link>
              <Link
                href="/failures/search"
                className="px-3.5 py-2 text-sm font-medium rounded-lg bg-slate-900 border border-slate-700 text-slate-200 hover:bg-slate-800 transition"
              >
                Find Similar Failures
              </Link>
              <button
                onClick={handleSync}
                disabled={syncing}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow transition disabled:opacity-50 flex items-center gap-2"
              >
                {syncing ? (
                  <>
                    <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                    Syncing...
                  </>
                ) : (
                  <>
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                    Sync Failures
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Sync notification */}
          {syncMessage && (
            <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm flex items-center justify-between">
              <span>{syncMessage}</span>
              <button onClick={() => setSyncMessage(null)} className="text-emerald-400 hover:text-white">✕</button>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
              {error}
            </div>
          )}

          {/* Metrics Overview Cards */}
          {metrics && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 shadow-sm">
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Total Failures</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white">{metrics.total_failure_events}</span>
                  <span className="text-xs text-slate-400">normalized events</span>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 shadow-sm">
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Semantic Clusters</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-white">{metrics.total_clusters}</span>
                  <span className="text-xs text-emerald-400 font-medium">
                    {metrics.clusters_by_status.investigating || 0} investigating
                  </span>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 shadow-sm">
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Critical / High Severity</span>
                <div className="mt-2 flex items-baseline gap-2">
                  <span className="text-2xl font-bold text-rose-400">
                    {(metrics.events_by_severity.critical || 0) + (metrics.events_by_severity.high || 0)}
                  </span>
                  <span className="text-xs text-slate-400">
                    ({metrics.events_by_severity.critical || 0} critical, {metrics.events_by_severity.high || 0} high)
                  </span>
                </div>
              </div>

              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 shadow-sm">
                <span className="text-xs font-medium text-slate-400 uppercase tracking-wider">Embedding Provider</span>
                <div className="mt-2 flex items-center gap-2">
                  {metrics.vector_search_available ? (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                      <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                      Active: {metrics.embedding_provider}
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 px-2 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
                      Lexical Fallback Active
                    </span>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Filters & Search */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 max-w-md">
              <input
                type="text"
                placeholder="Search error messages..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full px-3.5 py-2 text-sm bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 transition"
              />
              <button
                type="submit"
                className="px-3.5 py-2 text-sm bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg transition"
              >
                Search
              </button>
            </form>

            <div className="flex flex-wrap items-center gap-3">
              <div>
                <select
                  value={severityFilter}
                  onChange={(e) => {
                    setSeverityFilter(e.target.value);
                    setPage(1);
                  }}
                  className="px-3 py-2 text-sm bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="all">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>

              <div>
                <select
                  value={categoryFilter}
                  onChange={(e) => {
                    setCategoryFilter(e.target.value);
                    setPage(1);
                  }}
                  className="px-3 py-2 text-sm bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500"
                >
                  <option value="all">All Categories</option>
                  <option value="runtime_error">Runtime Error</option>
                  <option value="eval_failure">Evaluation Failure</option>
                  <option value="safety_failure">Safety Failure</option>
                  <option value="tool_error">Tool Error</option>
                  <option value="timeout">Timeout</option>
                </select>
              </div>
            </div>
          </div>

          {/* Failure Events Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between">
              <h2 className="text-base font-semibold text-white">Failure Event Feed</h2>
              <span className="text-xs text-slate-400">Total {total} events</span>
            </div>

            {loading ? (
              <div className="p-12 text-center text-slate-400 text-sm">Loading failure events...</div>
            ) : events.length === 0 ? (
              <div className="p-12 text-center text-slate-400 text-sm space-y-2">
                <p>No failure events found matching your criteria.</p>
                <p className="text-xs text-slate-500">Click &ldquo;Sync Failures&rdquo; above to ingest errors from runs, spans, and benchmarks.</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs text-slate-400 bg-slate-950/40">
                      <th className="py-3 px-4 font-medium">Severity</th>
                      <th className="py-3 px-4 font-medium">Source / Type</th>
                      <th className="py-3 px-4 font-medium">Agent / Version</th>
                      <th className="py-3 px-4 font-medium">Sanitized Error Summary</th>
                      <th className="py-3 px-4 font-medium">Cluster Assignment</th>
                      <th className="py-3 px-4 font-medium">Occurred At</th>
                      <th className="py-3 px-4 font-medium text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {events.map((ev) => (
                      <tr key={ev.id} className="hover:bg-slate-800/30 transition">
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          {getSeverityBadge(ev.severity)}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                            {ev.source_type}
                          </span>
                          <span className="block text-[11px] text-slate-500 mt-0.5">
                            {ev.failure_category}
                          </span>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          {ev.agent_name ? (
                            <div>
                              <span className="font-medium text-slate-200">{ev.agent_name}</span>
                              {ev.agent_version && (
                                <span className="text-xs text-slate-400 block">v{ev.agent_version}</span>
                              )}
                            </div>
                          ) : (
                            <span className="text-slate-500 text-xs">—</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 max-w-md">
                          <p className="text-slate-200 line-clamp-2 font-mono text-xs">
                            {ev.error_summary}
                          </p>
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap">
                          {ev.cluster_id ? (
                            <Link
                              href={`/failures/clusters/${ev.cluster_id}`}
                              className="text-xs font-medium text-emerald-400 hover:text-emerald-300 underline underline-offset-2"
                            >
                              View Cluster
                            </Link>
                          ) : (
                            <span className="text-xs text-slate-500 italic">Unassigned</span>
                          )}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap text-xs text-slate-400">
                          {new Date(ev.occurred_at).toLocaleString()}
                        </td>
                        <td className="py-3.5 px-4 whitespace-nowrap text-right">
                          <Link
                            href={`/failures/search?event_id=${ev.id}`}
                            className="inline-flex items-center gap-1 text-xs px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
                          >
                            Find Similar
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="px-6 py-3.5 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                <span>
                  Page {page} of {totalPages} ({total} items)
                </span>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page <= 1}
                    className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed transition"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                    disabled={page >= totalPages}
                    className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40 disabled:cursor-not-allowed transition"
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
