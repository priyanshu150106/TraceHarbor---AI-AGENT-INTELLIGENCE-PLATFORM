"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchFailureClusters, triggerClusteringJob, updateClusterStatus } from "@/lib/api";
import { FailureClusterSummary } from "@/lib/types";

export default function FailureClustersPage() {
  const [clusters, setClusters] = useState<FailureClusterSummary[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [statusFilter, setStatusFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [searchTerm, setSearchTerm] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Clustering execution state
  const [showRunModal, setShowRunModal] = useState(false);
  const [runningJob, setRunningJob] = useState(false);
  const [threshold, setThreshold] = useState(0.85);
  const [minClusterSize, setMinClusterSize] = useState(2);
  const [jobResult, setJobResult] = useState<string | null>(null);

  const loadClusters = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetchFailureClusters({
        page,
        pageSize,
        status: statusFilter,
        category: categoryFilter,
        search: searchTerm || undefined,
      });
      setClusters(res.items);
      setTotal(res.total);
      setTotalPages(res.total_pages);
    } catch (err: any) {
      setError(err.message || "Failed to load failure clusters.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadClusters();
  }, [page, statusFilter, categoryFilter]);

  const handleRunClustering = async () => {
    setRunningJob(true);
    setJobResult(null);
    try {
      const res = await triggerClusteringJob({
        similarity_threshold: threshold,
        min_cluster_size: minClusterSize,
      });
      setJobResult(
        `Clustering completed: ${res.clusters_created} new clusters created, ${res.clusters_updated} updated, ${res.events_assigned} events assigned.`
      );
      setShowRunModal(false);
      await loadClusters();
    } catch (err: any) {
      setError(err.message || "Clustering job failed.");
    } finally {
      setRunningJob(false);
    }
  };

  const handleQuickStatusChange = async (clusterId: string, newStatus: string) => {
    try {
      await updateClusterStatus(clusterId, {
        status: newStatus,
        resolution_notes: `Status changed to ${newStatus} from clusters overview.`,
      });
      await loadClusters();
    } catch (err: any) {
      setError(err.message || "Failed to update cluster status.");
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case "new":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400" />
            NEW
          </span>
        );
      case "investigating":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-pulse" />
            INVESTIGATING
          </span>
        );
      case "resolved":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
            RESOLVED
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-slate-500/10 text-slate-400 border border-slate-500/30">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
            IGNORED
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
                <Link href="/failures" className="text-slate-400 hover:text-white text-sm transition">
                  ← Failure Intelligence
                </Link>
                <span className="text-slate-600">/</span>
                <h1 className="text-2xl font-bold tracking-tight text-white">Semantic Clusters</h1>
              </div>
              <p className="text-sm text-slate-400 mt-1">
                Aggregated failure patterns grouped by vector similarity to accelerate root-cause triage.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/failures/search"
                className="px-3.5 py-2 text-sm font-medium rounded-lg bg-slate-900 border border-slate-700 text-slate-200 hover:bg-slate-800 transition"
              >
                Find Similar Failures
              </Link>
              <button
                onClick={() => setShowRunModal(true)}
                className="px-4 py-2 text-sm font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white shadow transition flex items-center gap-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
                </svg>
                Run Clustering Job
              </button>
            </div>
          </div>

          {/* Job Success Notification */}
          {jobResult && (
            <div className="p-3.5 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-sm flex items-center justify-between">
              <span>{jobResult}</span>
              <button onClick={() => setJobResult(null)} className="text-emerald-400 hover:text-white">✕</button>
            </div>
          )}

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
              {error}
            </div>
          )}

          {/* Status Filter Tabs */}
          <div className="flex flex-wrap items-center justify-between gap-4 border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2">
              {["all", "new", "investigating", "resolved", "ignored"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setStatusFilter(tab);
                    setPage(1);
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium uppercase tracking-wider transition ${
                    statusFilter === tab
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                      : "text-slate-400 hover:text-slate-200 hover:bg-slate-800/40"
                  }`}
                >
                  {tab}
                </button>
              ))}
            </div>

            <div className="flex items-center gap-3">
              <input
                type="text"
                placeholder="Search cluster title..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    setPage(1);
                    loadClusters();
                  }
                }}
                className="px-3 py-1.5 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500 w-56"
              />
              <select
                value={categoryFilter}
                onChange={(e) => {
                  setCategoryFilter(e.target.value);
                  setPage(1);
                }}
                className="px-3 py-1.5 text-xs bg-slate-900 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500"
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

          {/* Clusters List */}
          {loading ? (
            <div className="p-16 text-center text-slate-400 text-sm">Loading failure clusters...</div>
          ) : clusters.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-400 text-sm space-y-3">
              <p className="font-semibold text-slate-300">No failure clusters found.</p>
              <p className="text-xs text-slate-500 max-w-md mx-auto">
                Trigger a clustering job above to group similar failure events using vector similarity and PostgreSQL pgvector.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4">
              {clusters.map((cluster) => (
                <div
                  key={cluster.id}
                  className="bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 rounded-xl p-5 shadow-sm transition space-y-4"
                >
                  <div className="flex flex-col md:flex-row md:items-start justify-between gap-3">
                    <div className="space-y-1">
                      <div className="flex items-center gap-2.5 flex-wrap">
                        {getStatusBadge(cluster.status)}
                        <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                          {cluster.dominant_category}
                        </span>
                        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                          {cluster.event_count} events
                        </span>
                      </div>
                      <Link
                        href={`/failures/clusters/${cluster.id}`}
                        className="text-base font-semibold text-white hover:text-emerald-400 transition block mt-1"
                      >
                        {cluster.title}
                      </Link>
                    </div>

                    <div className="flex items-center gap-2 self-start">
                      <select
                        value={cluster.status}
                        onChange={(e) => handleQuickStatusChange(cluster.id, e.target.value)}
                        className="px-2.5 py-1 text-xs bg-slate-950 border border-slate-800 rounded text-slate-300 focus:outline-none focus:border-emerald-500"
                      >
                        <option value="new">Mark New</option>
                        <option value="investigating">Mark Investigating</option>
                        <option value="resolved">Mark Resolved</option>
                        <option value="ignored">Mark Ignored</option>
                      </select>
                      <Link
                        href={`/failures/clusters/${cluster.id}`}
                        className="px-3 py-1 text-xs font-medium rounded bg-emerald-600/90 hover:bg-emerald-500 text-white transition"
                      >
                        Investigate Evidence →
                      </Link>
                    </div>
                  </div>

                  {/* Representative Summary Excerpt */}
                  {cluster.representative_summary && (
                    <div className="bg-slate-950/60 border border-slate-800/80 rounded-lg p-3 text-xs font-mono text-slate-300 line-clamp-2">
                      {cluster.representative_summary}
                    </div>
                  )}

                  {/* Bottom Metadata Bar */}
                  <div className="flex flex-wrap items-center justify-between gap-3 pt-2 text-xs text-slate-400 border-t border-slate-800/60">
                    <div className="flex items-center gap-4 flex-wrap">
                      {cluster.affected_agents.length > 0 && (
                        <span>
                          <strong className="text-slate-300">Agents:</strong>{" "}
                          {cluster.affected_agents.slice(0, 3).join(", ")}
                          {cluster.affected_agents.length > 3 && ` +${cluster.affected_agents.length - 3} more`}
                        </span>
                      )}
                      <span>
                        <strong className="text-slate-300">First Seen:</strong>{" "}
                        {new Date(cluster.first_seen_at).toLocaleDateString()}
                      </span>
                      <span>
                        <strong className="text-slate-300">Last Seen:</strong>{" "}
                        {new Date(cluster.last_seen_at).toLocaleString()}
                      </span>
                    </div>

                    {/* Severity distribution pills */}
                    <div className="flex items-center gap-1.5">
                      {Object.entries(cluster.severity_distribution).map(([sev, cnt]) => (
                        <span
                          key={sev}
                          className="px-2 py-0.5 rounded text-[11px] font-mono bg-slate-800/80 text-slate-300"
                        >
                          {sev}: {cnt}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between text-xs text-slate-400 pt-2">
              <span>Page {page} of {totalPages} ({total} clusters)</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page <= 1}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page >= totalPages}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}

          {/* Run Clustering Job Modal */}
          {showRunModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
              <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-md w-full p-6 space-y-4 shadow-xl">
                <div className="flex items-center justify-between">
                  <h3 className="text-lg font-bold text-white">Execute Clustering Job</h3>
                  <button onClick={() => setShowRunModal(false)} className="text-slate-400 hover:text-white">✕</button>
                </div>
                <p className="text-xs text-slate-400">
                  Runs incremental cosine similarity clustering against PostgreSQL pgvector embeddings.
                  Failures above the similarity threshold join the nearest cluster.
                </p>

                <div className="space-y-3 pt-2">
                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Cosine Similarity Threshold ({threshold})
                    </label>
                    <input
                      type="range"
                      min="0.60"
                      max="0.95"
                      step="0.05"
                      value={threshold}
                      onChange={(e) => setThreshold(parseFloat(e.target.value))}
                      className="w-full"
                    />
                    <div className="flex justify-between text-[11px] text-slate-500 mt-0.5">
                      <span>0.60 (Broader)</span>
                      <span>0.85 (Conservative)</span>
                      <span>0.95 (Strict)</span>
                    </div>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-slate-300 mb-1">
                      Minimum Cluster Size ({minClusterSize})
                    </label>
                    <input
                      type="number"
                      min="1"
                      max="10"
                      value={minClusterSize}
                      onChange={(e) => setMinClusterSize(parseInt(e.target.value) || 2)}
                      className="w-full px-3 py-2 text-sm bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500"
                    />
                    <span className="text-[11px] text-slate-500">
                      Isolated failures below this size remain unassigned.
                    </span>
                  </div>
                </div>

                <div className="flex items-center justify-end gap-2 pt-4 border-t border-slate-800">
                  <button
                    onClick={() => setShowRunModal(false)}
                    className="px-4 py-2 text-xs font-medium rounded-lg text-slate-300 hover:bg-slate-800"
                  >
                    Cancel
                  </button>
                  <button
                    onClick={handleRunClustering}
                    disabled={runningJob}
                    className="px-4 py-2 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50"
                  >
                    {runningJob ? "Clustering..." : "Run Clustering"}
                  </button>
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
