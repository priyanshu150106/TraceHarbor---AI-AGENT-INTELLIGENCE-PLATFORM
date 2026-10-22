"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import React, { Suspense, useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import {
  createSafetyCampaign,
  fetchSafetyAgents,
  fetchSafetyCampaigns,
  fetchSafetyDatasets,
} from "@/lib/api";
import {
  ApprovedAgent,
  SafetyCampaignSummary,
} from "@/lib/types";

function SafetyCampaignsContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [campaigns, setCampaigns] = useState<SafetyCampaignSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // New campaign modal
  const [showModal, setShowModal] = useState(false);
  const [datasets, setDatasets] = useState<any[]>([]);
  const [agents, setAgents] = useState<ApprovedAgent[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(false);

  // Form fields
  const [campName, setCampName] = useState("");
  const [campDesc, setCampDesc] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedAgentIndex, setSelectedAgentIndex] = useState<number>(0);
  const [timeoutSeconds, setTimeoutSeconds] = useState(10);
  const [enableLlmJudge, setEnableLlmJudge] = useState(false);
  const [runSync, setRunSync] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const loadCampaigns = (p = page, s = statusFilter, q = search) => {
    setLoading(true);
    setError(null);
    fetchSafetyCampaigns({
      page: p,
      pageSize: 10,
      status: s === "all" ? undefined : s,
      search: q || undefined,
    })
      .then((res) => {
        setCampaigns(res.items);
        setTotalPages(res.total_pages || 1);
        setTotalCount(res.total);
      })
      .catch((err) => setError(err.message || "Failed to load safety campaigns."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadCampaigns(1, statusFilter, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  useEffect(() => {
    if (searchParams.get("action") === "new") {
      openNewModal();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [searchParams]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadCampaigns(1, statusFilter, search);
  };

  const openNewModal = async () => {
    setShowModal(true);
    setSubmitError(null);
    setLoadingOptions(true);
    try {
      const [dsRes, agRes] = await Promise.all([
        fetchSafetyDatasets({ pageSize: 50 }),
        fetchSafetyAgents(),
      ]);
      setDatasets(dsRes.items);
      if (dsRes.items.length > 0 && !selectedDatasetId) {
        setSelectedDatasetId(dsRes.items[0].id);
      }
      setAgents(agRes);
      if (!campName) {
        setCampName(`Safety Red-Team - ${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
      }
    } catch (err: any) {
      setSubmitError(err.message || "Failed to load safety datasets or approved agents.");
    } finally {
      setLoadingOptions(false);
    }
  };

  const handleCreateCampaign = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!campName.trim() || !selectedDatasetId || agents.length === 0) {
      setSubmitError("Please fill in all required fields.");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);

    const selectedAgent = agents[selectedAgentIndex];
    try {
      const created = await createSafetyCampaign(
        {
          name: campName.trim(),
          description: campDesc.trim() || undefined,
          dataset_id: selectedDatasetId,
          agent_name: selectedAgent.agent_name,
          agent_version: selectedAgent.agent_version,
          config: {
            case_timeout_seconds: timeoutSeconds,
            enable_llm_judge: enableLlmJudge,
          },
        },
        runSync
      );
      setShowModal(false);
      router.push(`/safety/campaigns/${created.id}`);
    } catch (err: any) {
      setSubmitError(err.message || "Failed to launch safety campaign.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 antialiased overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <Navbar />

        <main className="p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
            <div>
              <div className="flex items-center space-x-2">
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                  Adversarial Suites
                </span>
                <span className="text-xs text-slate-400 font-mono">Safety Campaigns</span>
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-white mt-1">
                Safety Campaigns Explorer
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Launch, monitor, and inspect automated adversarial benchmarks across agent versions.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/safety/compare"
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-sm font-medium rounded-lg border border-slate-700 transition flex items-center space-x-2"
              >
                <svg className="w-4 h-4 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                </svg>
                <span>Compare</span>
              </Link>

              <button
                onClick={openNewModal}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg shadow-sm transition flex items-center space-x-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>Launch Campaign</span>
              </button>
            </div>
          </div>

          {/* Sub Navigation Bar */}
          <div className="flex items-center space-x-1 border-b border-slate-800 text-sm">
            <Link
              href="/safety"
              className="px-4 py-2 font-medium text-slate-400 hover:text-slate-200 transition"
            >
              <span>Overview</span>
            </Link>
            <Link
              href="/safety/campaigns"
              className="px-4 py-2 font-medium text-emerald-400 border-b-2 border-emerald-400 flex items-center space-x-2"
            >
              <span>Campaigns</span>
            </Link>
            <Link
              href="/safety/compare"
              className="px-4 py-2 font-medium text-slate-400 hover:text-slate-200 transition"
            >
              <span>Regression Compare</span>
            </Link>
          </div>

          {/* Filters Bar */}
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between bg-slate-900/60 p-4 rounded-xl border border-slate-800/80">
            <div className="flex items-center gap-2 w-full sm:w-auto">
              {["all", "completed", "running", "error"].map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    setStatusFilter(s);
                    setPage(1);
                  }}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium capitalize transition ${
                    statusFilter === s
                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                      : "bg-slate-800/80 text-slate-400 hover:text-slate-200 border border-slate-700/60"
                  }`}
                >
                  {s}
                </button>
              ))}
            </div>

            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 w-full sm:w-72">
              <input
                type="text"
                placeholder="Search campaigns..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
              />
              <button
                type="submit"
                className="px-3 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
              >
                Search
              </button>
            </form>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-sm flex items-center justify-between">
              <span>{error}</span>
              <button onClick={() => loadCampaigns()} className="text-xs underline font-medium">
                Retry
              </button>
            </div>
          )}

          {/* Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm text-slate-300">
                <thead className="bg-slate-950/60 text-xs uppercase text-slate-400 border-b border-slate-800 tracking-wider">
                  <tr>
                    <th className="px-5 py-3.5">Campaign Name</th>
                    <th className="px-5 py-3.5">Target Agent</th>
                    <th className="px-5 py-3.5">Dataset</th>
                    <th className="px-5 py-3.5">Safety Pass Rate</th>
                    <th className="px-5 py-3.5">Critical Breaches</th>
                    <th className="px-5 py-3.5">Status</th>
                    <th className="px-5 py-3.5">Created</th>
                    <th className="px-5 py-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60 font-sans">
                  {loading && (
                    <tr>
                      <td colSpan={8} className="px-5 py-12 text-center text-slate-400">
                        <div className="inline-block animate-spin h-5 w-5 border-2 border-emerald-400 border-t-transparent rounded-full mr-2" />
                        Loading safety campaigns...
                      </td>
                    </tr>
                  )}

                  {!loading && campaigns.length === 0 && (
                    <tr>
                      <td colSpan={8} className="px-5 py-12 text-center text-slate-400 space-y-2">
                        <p className="text-sm">No safety campaigns match your search.</p>
                        <button
                          onClick={openNewModal}
                          className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition"
                        >
                          Launch New Campaign
                        </button>
                      </td>
                    </tr>
                  )}

                  {!loading &&
                    campaigns.map((camp) => {
                      const rate =
                        camp.safety_pass_rate !== null && camp.safety_pass_rate !== undefined
                          ? (camp.safety_pass_rate * 100).toFixed(1)
                          : null;

                      return (
                        <tr key={camp.id} className="hover:bg-slate-800/40 transition">
                          <td className="px-5 py-3.5 font-medium text-white">
                            <Link
                              href={`/safety/campaigns/${camp.id}`}
                              className="hover:text-emerald-400 transition"
                            >
                              {camp.name}
                            </Link>
                            {camp.description && (
                              <p className="text-xs text-slate-500 truncate max-w-xs">{camp.description}</p>
                            )}
                          </td>
                          <td className="px-5 py-3.5">
                            <span className="font-mono text-xs text-slate-200">
                              {camp.agent_name}
                            </span>
                            <span className="ml-1.5 px-1.5 py-0.5 rounded text-[10px] bg-slate-800 text-slate-300 border border-slate-700">
                              {camp.agent_version}
                            </span>
                          </td>
                          <td className="px-5 py-3.5 text-xs text-slate-300">
                            {camp.dataset_name || "Safety Benchmark"}
                          </td>
                          <td className="px-5 py-3.5">
                            {rate !== null ? (
                              <div className="flex items-center space-x-2">
                                <span
                                  className={`text-xs px-2 py-0.5 rounded font-mono font-medium ${
                                    Number(rate) >= 90
                                      ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                      : Number(rate) >= 70
                                      ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                      : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                  }`}
                                >
                                  {rate}%
                                </span>
                                <span className="text-xs text-slate-500">
                                  ({camp.passed_tests}/{camp.total_tests})
                                </span>
                              </div>
                            ) : (
                              <span className="text-xs text-slate-500">—</span>
                            )}
                          </td>
                          <td className="px-5 py-3.5">
                            {camp.critical_failures > 0 ? (
                              <span className="px-2 py-0.5 rounded text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/30 flex items-center space-x-1 w-max">
                                <span>{camp.critical_failures} Breaches</span>
                              </span>
                            ) : (
                              <span className="text-xs text-slate-400 font-mono">0</span>
                            )}
                          </td>
                          <td className="px-5 py-3.5">
                            <span
                              className={`px-2 py-0.5 text-xs rounded-full font-medium ${
                                camp.status === "completed"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : camp.status === "running"
                                  ? "bg-sky-500/10 text-sky-400 border border-sky-500/20 animate-pulse"
                                  : camp.status === "error"
                                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                  : "bg-slate-800 text-slate-300"
                              }`}
                            >
                              {camp.status}
                            </span>
                          </td>
                          <td className="px-5 py-3.5 text-xs text-slate-500">
                            {new Date(camp.created_at).toLocaleDateString()}
                          </td>
                          <td className="px-5 py-3.5 text-right space-x-2">
                            <Link
                              href={`/safety/campaigns/${camp.id}`}
                              className="text-xs px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 transition"
                            >
                              Inspect
                            </Link>
                          </td>
                        </tr>
                      );
                    })}
                </tbody>
              </table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="p-4 border-t border-slate-800 flex items-center justify-between text-xs text-slate-400">
                <span>
                  Showing page {page} of {totalPages} ({totalCount} total)
                </span>
                <div className="flex gap-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => {
                      setPage((prev) => prev - 1);
                      loadCampaigns(page - 1);
                    }}
                    className="px-3 py-1 bg-slate-800 disabled:opacity-40 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 transition"
                  >
                    Previous
                  </button>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => {
                      setPage((prev) => prev + 1);
                      loadCampaigns(page + 1);
                    }}
                    className="px-3 py-1 bg-slate-800 disabled:opacity-40 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 transition"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Launch Campaign Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-slate-950/80 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div className="flex items-center space-x-2">
                <div className="w-8 h-8 rounded-lg bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400">
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <div>
                  <h3 className="text-base font-semibold text-white">Launch Safety Campaign</h3>
                  <p className="text-xs text-slate-400">Run adversarial test cases against approved agent</p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white transition"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            {submitError && (
              <div className="p-3 bg-rose-500/10 border border-rose-500/30 rounded-lg text-rose-400 text-xs">
                {submitError}
              </div>
            )}

            <form onSubmit={handleCreateCampaign} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Campaign Title *
                </label>
                <input
                  type="text"
                  required
                  value={campName}
                  onChange={(e) => setCampName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                  placeholder="e.g. Q4 Red-Teaming Baseline"
                />
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Target Safety Dataset *
                </label>
                {loadingOptions ? (
                  <div className="text-xs text-slate-500">Loading datasets...</div>
                ) : (
                  <select
                    value={selectedDatasetId}
                    onChange={(e) => setSelectedDatasetId(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500"
                  >
                    {datasets.map((d) => (
                      <option key={d.id} value={d.id}>
                        {d.name} ({d.case_count} cases)
                      </option>
                    ))}
                  </select>
                )}
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Target Approved Agent Version *
                </label>
                {loadingOptions ? (
                  <div className="text-xs text-slate-500">Loading approved agents...</div>
                ) : (
                  <select
                    value={selectedAgentIndex}
                    onChange={(e) => setSelectedAgentIndex(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-emerald-500 font-mono text-xs"
                  >
                    {agents.map((ag, idx) => (
                      <option key={idx} value={idx}>
                        {ag.agent_name} (v{ag.agent_version}) — {ag.description}
                      </option>
                    ))}
                  </select>
                )}
              </div>

              {/* Safety Boundary Config */}
              <div className="p-3 bg-slate-950/60 border border-slate-800 rounded-lg space-y-3">
                <span className="text-xs font-semibold text-slate-300 uppercase tracking-wider block">
                  Execution Boundary Guardrails
                </span>

                <div className="flex items-center justify-between text-xs">
                  <div>
                    <span className="text-slate-200 font-medium">Per-Case Timeout</span>
                    <p className="text-slate-500 text-[11px]">Enforce non-blocking test boundary</p>
                  </div>
                  <div className="flex items-center space-x-1">
                    <input
                      type="number"
                      min={1}
                      max={60}
                      value={timeoutSeconds}
                      onChange={(e) => setTimeoutSeconds(Number(e.target.value))}
                      className="w-16 bg-slate-900 border border-slate-700 rounded px-2 py-1 text-slate-200 text-xs text-right"
                    />
                    <span className="text-slate-400">sec</span>
                  </div>
                </div>

                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800/80">
                  <div>
                    <span className="text-slate-200 font-medium">Optional LLM Judge</span>
                    <p className="text-slate-500 text-[11px]">Provider-neutral heuristic layer</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableLlmJudge}
                      onChange={(e) => setEnableLlmJudge(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-8 h-4 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-emerald-600"></div>
                  </label>
                </div>

                <div className="flex items-center justify-between text-xs pt-1 border-t border-slate-800/80">
                  <div>
                    <span className="text-slate-200 font-medium">Synchronous Execution</span>
                    <p className="text-slate-500 text-[11px]">Wait for benchmark to complete before redirecting</p>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={runSync}
                      onChange={(e) => setRunSync(e.target.checked)}
                      className="sr-only peer"
                    />
                    <div className="w-8 h-4 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-slate-300 after:border after:rounded-full after:h-3 after:w-3 after:transition-all peer-checked:bg-emerald-600"></div>
                  </label>
                </div>
              </div>

              <div className="flex items-center justify-end space-x-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium rounded-lg transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-50 text-white text-xs font-medium rounded-lg shadow-sm transition flex items-center space-x-1.5"
                >
                  {submitting && (
                    <div className="animate-spin h-3.5 w-3.5 border-2 border-white border-t-transparent rounded-full" />
                  )}
                  <span>{submitting ? "Executing Benchmark..." : "Execute Campaign"}</span>
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

export default function SafetyCampaignsPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen bg-slate-950 text-slate-100 antialiased overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <Navbar />
            <div className="p-12 text-center text-slate-400 text-xs">
              Loading safety campaigns...
            </div>
          </div>
        </div>
      }
    >
      <SafetyCampaignsContent />
    </Suspense>
  );
}
