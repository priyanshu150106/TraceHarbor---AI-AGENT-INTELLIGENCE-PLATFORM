"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchFailureClusterDetail, updateClusterStatus } from "@/lib/api";
import { FailureClusterDetail } from "@/lib/types";

export default function FailureClusterDetailPage() {
  const params = useParams();
  const clusterId = params?.id as string;

  const [cluster, setCluster] = useState<FailureClusterDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Status update form state
  const [newStatus, setNewStatus] = useState("new");
  const [resolutionNotes, setResolutionNotes] = useState("");
  const [updating, setUpdating] = useState(false);
  const [updateSuccess, setUpdateSuccess] = useState(false);

  const loadDetail = async () => {
    if (!clusterId) return;
    setLoading(true);
    setError(null);
    try {
      const data = await fetchFailureClusterDetail(clusterId);
      setCluster(data);
      setNewStatus(data.status);
      setResolutionNotes(data.resolution_notes || "");
    } catch (err: any) {
      setError(err.message || "Failed to load cluster details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadDetail();
  }, [clusterId]);

  const handleStatusSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!clusterId) return;
    setUpdating(true);
    setUpdateSuccess(false);
    try {
      await updateClusterStatus(clusterId, {
        status: newStatus,
        resolution_notes: resolutionNotes,
      });
      setUpdateSuccess(true);
      await loadDetail();
      setTimeout(() => setUpdateSuccess(false), 3000);
    } catch (err: any) {
      setError(err.message || "Failed to update cluster status.");
    } finally {
      setUpdating(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 antialiased overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar />
        <main className="flex-1 overflow-y-auto p-6 space-y-6">
          {/* Breadcrumb Header */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-400">
              <Link href="/failures" className="hover:text-white transition">
                Failures
              </Link>
              <span>/</span>
              <Link href="/failures/clusters" className="hover:text-white transition">
                Clusters
              </Link>
              <span>/</span>
              <span className="text-slate-200 font-mono text-xs">{clusterId?.slice(0, 8)}...</span>
            </div>
            <Link
              href="/failures/clusters"
              className="text-xs px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:bg-slate-800 transition"
            >
              ← Back to Clusters
            </Link>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
              {error}
            </div>
          )}

          {loading ? (
            <div className="p-16 text-center text-slate-400 text-sm">Loading cluster investigation details...</div>
          ) : !cluster ? (
            <div className="p-16 text-center text-slate-400 text-sm">Cluster not found.</div>
          ) : (
            <>
              {/* Cluster Overview Header Card */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4">
                <div className="flex flex-col md:flex-row md:items-start justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2.5 flex-wrap">
                      <span className="px-2.5 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        {cluster.status.toUpperCase()}
                      </span>
                      <span className="font-mono text-xs px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        {cluster.dominant_category}
                      </span>
                      <span className="text-xs text-slate-400">
                        Algorithm: {cluster.algorithm_version} (Threshold {cluster.similarity_threshold || 0.85})
                      </span>
                    </div>
                    <h1 className="text-xl font-bold text-white pt-1">{cluster.title}</h1>
                    <p className="text-xs text-slate-500 font-mono">Cluster ID: {cluster.id}</p>
                  </div>

                  <div className="flex items-center gap-2">
                    <Link
                      href={`/failures/search?event_id=${cluster.recent_events[0]?.id || ""}`}
                      className="px-3.5 py-1.5 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
                    >
                      Search Similar
                    </Link>
                  </div>
                </div>

                {/* Key Metrics Strip */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 pt-3 border-t border-slate-800/80 text-xs">
                  <div>
                    <span className="text-slate-400 block">Total Affected Events</span>
                    <span className="text-lg font-bold text-white">{cluster.event_count}</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">First Seen</span>
                    <span className="text-slate-200 font-medium">
                      {new Date(cluster.first_seen_at).toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Last Seen</span>
                    <span className="text-slate-200 font-medium">
                      {new Date(cluster.last_seen_at).toLocaleString()}
                    </span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Severity Distribution</span>
                    <div className="flex items-center gap-1.5 mt-1">
                      {Object.entries(cluster.severity_distribution).map(([sev, cnt]) => (
                        <span key={sev} className="px-1.5 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-slate-300">
                          {sev}: {cnt}
                        </span>
                      ))}
                    </div>
                  </div>
                </div>
              </div>

              {/* Status & Resolution Form Card */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                <h2 className="text-sm font-semibold text-white flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  Investigation Status & Developer Notes
                </h2>

                {updateSuccess && (
                  <div className="p-3 rounded-lg bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs">
                    Cluster investigation status and notes updated successfully!
                  </div>
                )}

                <form onSubmit={handleStatusSubmit} className="space-y-3">
                  <div className="grid grid-cols-1 sm:grid-cols-4 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Investigation Status
                      </label>
                      <select
                        value={newStatus}
                        onChange={(e) => setNewStatus(e.target.value)}
                        className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 focus:outline-none focus:border-emerald-500"
                      >
                        <option value="new">New (Unreviewed)</option>
                        <option value="investigating">Investigating (Active)</option>
                        <option value="resolved">Resolved (Fix Deployed)</option>
                        <option value="ignored">Ignored (Wontfix / Known)</option>
                      </select>
                    </div>

                    <div className="sm:col-span-3">
                      <label className="block text-xs font-medium text-slate-300 mb-1">
                        Resolution Notes / Root Cause Findings
                      </label>
                      <textarea
                        rows={2}
                        placeholder="Document investigation findings, PR links, or mitigation actions..."
                        value={resolutionNotes}
                        onChange={(e) => setResolutionNotes(e.target.value)}
                        className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>

                  <div className="flex justify-end">
                    <button
                      type="submit"
                      disabled={updating}
                      className="px-4 py-2 text-xs font-medium rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50 transition"
                    >
                      {updating ? "Saving..." : "Save Status & Notes"}
                    </button>
                  </div>
                </form>
              </div>

              {/* Supporting Evidence Grid */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Representative Sanitized Example */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
                  <h3 className="text-sm font-semibold text-white">Representative Sanitized Example</h3>
                  <p className="text-xs text-slate-400">
                    Redacted error summary extracted from representative cluster members.
                  </p>
                  <pre className="p-3.5 rounded-lg bg-slate-950 border border-slate-800/80 text-xs font-mono text-slate-200 whitespace-pre-wrap overflow-x-auto max-h-48">
                    {cluster.representative_summary || "No error summary available."}
                  </pre>
                </div>

                {/* Affected Versions & Traces */}
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-white">Affected Agent Versions & Models</h3>
                    <div className="flex flex-wrap items-center gap-1.5 mt-2">
                      {cluster.affected_agents.length > 0 ? (
                        cluster.affected_agents.map((ag) => (
                          <span key={ag} className="px-2 py-0.5 rounded text-xs font-medium bg-slate-800 text-slate-200">
                            {ag}
                          </span>
                        ))
                      ) : (
                        <span className="text-xs text-slate-500">None recorded</span>
                      )}
                      {cluster.affected_models.map((mod) => (
                        <span key={mod} className="px-2 py-0.5 rounded text-xs font-mono bg-blue-500/10 text-blue-300 border border-blue-500/20">
                          {mod}
                        </span>
                      ))}
                    </div>
                  </div>

                  <div>
                    <h3 className="text-sm font-semibold text-white">Representative Trace Links</h3>
                    <div className="space-y-1.5 mt-2">
                      {cluster.representative_traces.length > 0 ? (
                        cluster.representative_traces.map((tr) => (
                          <div key={tr.run_id} className="flex items-center justify-between p-2 rounded bg-slate-950 text-xs border border-slate-800/80">
                            <span className="font-mono text-slate-300">Run: {tr.run_id.slice(0, 12)}...</span>
                            <Link
                              href={`/runs/${tr.run_id}`}
                              className="text-emerald-400 hover:text-emerald-300 font-medium underline"
                            >
                              Open Trace Explorer →
                            </Link>
                          </div>
                        ))
                      ) : (
                        <span className="text-xs text-slate-500">No traces linked</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              {/* Status Audit Trail */}
              {cluster.status_history.length > 0 && (
                <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-5 space-y-3">
                  <h3 className="text-sm font-semibold text-white">Status Change Audit Trail</h3>
                  <div className="space-y-2">
                    {cluster.status_history.map((hist) => (
                      <div key={hist.id} className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/70 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                        <div className="flex items-center gap-2">
                          <span className="text-slate-400 font-mono">{hist.previous_status}</span>
                          <span className="text-slate-600">→</span>
                          <span className="font-semibold text-emerald-400 uppercase">{hist.new_status}</span>
                          {hist.resolution_notes && (
                            <span className="text-slate-300 italic pl-2 border-l border-slate-800">
                              &ldquo;{hist.resolution_notes}&rdquo;
                            </span>
                          )}
                        </div>
                        <span className="text-slate-500 text-[11px] whitespace-nowrap">
                          {new Date(hist.changed_at).toLocaleString()}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Member Failure Events Table */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
                <div className="px-6 py-4 border-b border-slate-800/80 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Recent Member Failure Events</h3>
                  <span className="text-xs text-slate-400">Showing up to 20 member events</span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs">
                    <thead>
                      <tr className="border-b border-slate-800 text-slate-400 bg-slate-950/40">
                        <th className="py-2.5 px-4 font-medium">Severity</th>
                        <th className="py-2.5 px-4 font-medium">Source</th>
                        <th className="py-2.5 px-4 font-medium">Agent</th>
                        <th className="py-2.5 px-4 font-medium">Sanitized Error Summary</th>
                        <th className="py-2.5 px-4 font-medium">Occurred At</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {cluster.recent_events.map((ev) => (
                        <tr key={ev.id} className="hover:bg-slate-800/20 transition">
                          <td className="py-2.5 px-4 whitespace-nowrap font-semibold">
                            {ev.severity.toUpperCase()}
                          </td>
                          <td className="py-2.5 px-4 whitespace-nowrap font-mono text-slate-400">
                            {ev.source_type}
                          </td>
                          <td className="py-2.5 px-4 whitespace-nowrap">
                            {ev.agent_name ? `${ev.agent_name} (v${ev.agent_version || "?"})` : "—"}
                          </td>
                          <td className="py-2.5 px-4 max-w-md font-mono text-slate-300 line-clamp-1">
                            {ev.error_summary}
                          </td>
                          <td className="py-2.5 px-4 whitespace-nowrap text-slate-400">
                            {new Date(ev.occurred_at).toLocaleString()}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
