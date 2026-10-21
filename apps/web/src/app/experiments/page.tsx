"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import {
  createExperiment,
  fetchApprovedAgents,
  fetchDatasets,
  fetchExperiments,
} from "@/lib/api";
import {
  ApprovedAgent,
  DatasetSummary,
  ExperimentSummary,
} from "@/lib/types";

export default function ExperimentsPage() {
  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalCount, setTotalCount] = useState(0);

  // New experiment modal state
  const [showModal, setShowModal] = useState(false);
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [agents, setAgents] = useState<ApprovedAgent[]>([]);
  const [loadingOptions, setLoadingOptions] = useState(false);

  // Form fields
  const [expName, setExpName] = useState("");
  const [expDesc, setExpDesc] = useState("");
  const [selectedDatasetId, setSelectedDatasetId] = useState("");
  const [selectedAgentIndex, setSelectedAgentIndex] = useState<number>(0);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const loadExperiments = (p = page, s = statusFilter, q = search) => {
    setLoading(true);
    setError(null);
    fetchExperiments({
      page: p,
      pageSize: 10,
      status: s === "all" ? undefined : s,
      search: q || undefined,
    })
      .then((res) => {
        setExperiments(res.items);
        setTotalPages(res.total_pages || 1);
        setTotalCount(res.total);
      })
      .catch((err) => setError(err.message || "Failed to load experiments."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadExperiments(1, statusFilter, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [statusFilter]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadExperiments(1, statusFilter, search);
  };

  const openNewModal = async () => {
    setShowModal(true);
    setSubmitError(null);
    setLoadingOptions(true);
    try {
      const [dsRes, agRes] = await Promise.all([
        fetchDatasets({ pageSize: 50 }),
        fetchApprovedAgents(),
      ]);
      setDatasets(dsRes.items);
      if (dsRes.items.length > 0 && !selectedDatasetId) {
        setSelectedDatasetId(dsRes.items[0].id);
      }
      setAgents(agRes);
      if (!expName) {
        setExpName(`Eval Run - ${new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}`);
      }
    } catch (err: any) {
      setSubmitError(err.message || "Failed to load datasets or agents.");
    } finally {
      setLoadingOptions(false);
    }
  };

  const handleCreateExperiment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!expName.trim() || !selectedDatasetId || agents.length === 0) {
      setSubmitError("Please fill in all required fields.");
      return;
    }
    const agent = agents[selectedAgentIndex];
    if (!agent) {
      setSubmitError("Selected agent is invalid.");
      return;
    }

    setSubmitting(true);
    setSubmitError(null);
    try {
      await createExperiment({
        name: expName.trim(),
        description: expDesc.trim() || undefined,
        dataset_id: selectedDatasetId,
        agent_name: agent.agent_name,
        agent_version: agent.agent_version,
      });
      setShowModal(false);
      setExpName("");
      setExpDesc("");
      loadExperiments(1, statusFilter, search);
    } catch (err: any) {
      setSubmitError(err.message || "Failed to start experiment.");
    } finally {
      setSubmitting(false);
    }
  };

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "completed":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            Completed
          </span>
        );
      case "running":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-blue-400 animate-pulse"></span>
            Running
          </span>
        );
      case "error":
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
            Error
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-300 border border-slate-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            {status}
          </span>
        );
    }
  };

  return (
    <div className="flex min-h-screen bg-[#070b14] text-slate-100 font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar />

        <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">
                  Evaluation Experiments
                </h1>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 rounded">
                  Phase 3
                </span>
              </div>
              <p className="text-sm text-slate-400 mt-1">
                Run deterministic evaluators and regression suites against approved agent versions.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/experiments/compare"
                className="inline-flex items-center gap-2 px-3.5 py-2 text-xs font-medium rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-200 border border-slate-700/80 transition-colors shadow-sm"
              >
                <svg
                  className="w-4 h-4 text-indigo-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                  />
                </svg>
                Compare Versions
              </Link>
              <button
                onClick={openNewModal}
                className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white shadow-lg shadow-indigo-500/25 transition-all transform active:scale-95"
              >
                <svg
                  className="w-4 h-4"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                  />
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                  />
                </svg>
                Start Experiment
              </button>
            </div>
          </div>

          {/* Quick Metrics */}
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
              <span className="text-xs text-slate-400 font-medium">Total Experiments</span>
              <p className="text-2xl font-bold text-white mt-1">{totalCount}</p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
              <span className="text-xs text-slate-400 font-medium">Completed</span>
              <p className="text-2xl font-bold text-emerald-400 mt-1">
                {experiments.filter((e) => e.status === "completed").length}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
              <span className="text-xs text-slate-400 font-medium">Active / Running</span>
              <p className="text-2xl font-bold text-blue-400 mt-1">
                {experiments.filter((e) => e.status === "running").length}
              </p>
            </div>
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4">
              <span className="text-xs text-slate-400 font-medium">Avg Pass Rate</span>
              <p className="text-2xl font-bold text-indigo-400 mt-1">
                {experiments.length > 0
                  ? `${Math.round(
                      (experiments
                        .filter((e) => e.pass_rate !== null)
                        .reduce((acc, curr) => acc + (curr.pass_rate || 0), 0) /
                        (experiments.filter((e) => e.pass_rate !== null).length || 1)) *
                        100
                    )}%`
                  : "—"}
              </p>
            </div>
          </div>

          {/* Filters & Search */}
          <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800/60">
            <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 w-full sm:w-80">
              <div className="relative flex-1">
                <svg
                  className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
                  />
                </svg>
                <input
                  type="text"
                  placeholder="Search by name, agent..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
                />
              </div>
              <button
                type="submit"
                className="px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition-colors border border-slate-700"
              >
                Search
              </button>
            </form>

            <div className="flex items-center gap-2 w-full sm:w-auto overflow-x-auto">
              {["all", "completed", "running", "error"].map((tab) => (
                <button
                  key={tab}
                  onClick={() => {
                    setStatusFilter(tab);
                    setPage(1);
                  }}
                  className={`px-3 py-1 text-xs rounded-lg font-medium transition-colors capitalize ${
                    statusFilter === tab
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "bg-slate-900/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800/80"
                  }`}
                >
                  {tab}
                </button>
              ))}
              <button
                onClick={() => loadExperiments(page, statusFilter, search)}
                title="Refresh list"
                className="p-1.5 text-slate-400 hover:text-white bg-slate-900/80 hover:bg-slate-800 border border-slate-800 rounded-lg transition-colors ml-1"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth="2"
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
              </button>
            </div>
          </div>

          {/* Table / Content */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden shadow-xl">
            {loading ? (
              <div className="py-20 flex flex-col items-center justify-center space-y-3">
                <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
                <span className="text-sm text-slate-400">Loading experiments...</span>
              </div>
            ) : error ? (
              <div className="p-8 text-center">
                <div className="inline-flex p-3 rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20 mb-3">
                  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <p className="text-sm font-semibold text-rose-300">{error}</p>
                <button
                  onClick={() => loadExperiments()}
                  className="mt-4 px-3 py-1.5 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700"
                >
                  Retry
                </button>
              </div>
            ) : experiments.length === 0 ? (
              <div className="py-16 px-4 text-center space-y-3">
                <div className="inline-flex p-3 rounded-full bg-slate-800 text-slate-400 mb-1">
                  <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="1.5"
                      d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z"
                    />
                  </svg>
                </div>
                <h3 className="text-base font-semibold text-white">No experiments found</h3>
                <p className="text-sm text-slate-400 max-w-sm mx-auto">
                  {search || statusFilter !== "all"
                    ? "No experiments match your search criteria."
                    : "No experiments have been run yet. Start your first evaluation against a golden dataset."}
                </p>
                <div className="pt-2">
                  <button
                    onClick={openNewModal}
                    className="inline-flex items-center gap-2 px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white"
                  >
                    Start First Experiment
                  </button>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse text-xs">
                  <thead>
                    <tr className="border-b border-slate-800 bg-slate-950/40 text-slate-400 uppercase tracking-wider font-semibold">
                      <th className="py-3 px-4">Experiment</th>
                      <th className="py-3 px-4">Agent Version</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4">Pass Rate</th>
                      <th className="py-3 px-4">Score</th>
                      <th className="py-3 px-4">Cases (P/F/E)</th>
                      <th className="py-3 px-4">Created</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {experiments.map((exp) => {
                      const rate =
                        exp.pass_rate !== null ? Math.round(exp.pass_rate * 100) : null;
                      return (
                        <tr
                          key={exp.id}
                          className="hover:bg-slate-800/30 transition-colors group"
                        >
                          <td className="py-3 px-4">
                            <Link
                              href={`/experiments/${exp.id}`}
                              className="font-medium text-slate-200 hover:text-indigo-400 transition-colors flex items-center gap-1.5"
                            >
                              {exp.name}
                            </Link>
                            {exp.description && (
                              <p className="text-[11px] text-slate-500 truncate max-w-xs mt-0.5">
                                {exp.description}
                              </p>
                            )}
                          </td>
                          <td className="py-3 px-4">
                            <div className="flex items-center gap-1.5">
                              <span className="font-mono text-indigo-300 font-semibold bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-800/40">
                                {exp.agent_name}
                              </span>
                              <span className="font-mono text-[11px] text-slate-400">
                                v{exp.agent_version}
                              </span>
                            </div>
                          </td>
                          <td className="py-3 px-4">{getStatusBadge(exp.status)}</td>
                          <td className="py-3 px-4">
                            {rate !== null ? (
                              <div className="w-28 space-y-1">
                                <div className="flex justify-between items-center text-[10px]">
                                  <span
                                    className={`font-bold ${
                                      rate >= 80
                                        ? "text-emerald-400"
                                        : rate >= 50
                                        ? "text-amber-400"
                                        : "text-rose-400"
                                    }`}
                                  >
                                    {rate}%
                                  </span>
                                </div>
                                <div className="w-full bg-slate-800 h-1.5 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full rounded-full ${
                                      rate >= 80
                                        ? "bg-emerald-500"
                                        : rate >= 50
                                        ? "bg-amber-500"
                                        : "bg-rose-500"
                                    }`}
                                    style={{ width: `${rate}%` }}
                                  ></div>
                                </div>
                              </div>
                            ) : (
                              <span className="text-slate-500">—</span>
                            )}
                          </td>
                          <td className="py-3 px-4 font-mono font-medium text-slate-300">
                            {exp.score !== null ? exp.score.toFixed(2) : "—"}
                          </td>
                          <td className="py-3 px-4">
                            <span className="inline-flex items-center gap-1 font-mono text-[11px]">
                              <span className="text-emerald-400 font-semibold">{exp.passed_cases}</span>
                              <span className="text-slate-600">/</span>
                              <span className="text-rose-400 font-semibold">{exp.failed_cases}</span>
                              <span className="text-slate-600">/</span>
                              <span className="text-amber-400 font-semibold">{exp.errored_cases}</span>
                              <span className="text-slate-500 text-[10px]">({exp.total_cases} total)</span>
                            </span>
                          </td>
                          <td className="py-3 px-4 text-slate-400 whitespace-nowrap">
                            {new Date(exp.created_at).toLocaleDateString([], {
                              month: "short",
                              day: "numeric",
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </td>
                          <td className="py-3 px-4 text-right whitespace-nowrap">
                            <div className="flex items-center justify-end gap-2">
                              <Link
                                href={`/experiments/compare?a=${exp.id}`}
                                title="Compare against this baseline"
                                className="px-2 py-1 bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white rounded border border-slate-700 text-[11px] transition-colors"
                              >
                                Compare
                              </Link>
                              <Link
                                href={`/experiments/${exp.id}`}
                                className="px-2.5 py-1 bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 hover:text-indigo-200 rounded border border-indigo-500/30 text-[11px] font-medium transition-colors"
                              >
                                Details →
                              </Link>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between px-4 py-3 border-t border-slate-800 bg-slate-950/40 text-xs text-slate-400">
                <span>
                  Page <strong className="text-slate-200">{page}</strong> of{" "}
                  <strong className="text-slate-200">{totalPages}</strong>
                </span>
                <div className="flex items-center gap-2">
                  <button
                    disabled={page <= 1}
                    onClick={() => {
                      setPage((p) => p - 1);
                      loadExperiments(page - 1, statusFilter, search);
                    }}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:pointer-events-none text-slate-300 border border-slate-700"
                  >
                    Previous
                  </button>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => {
                      setPage((p) => p + 1);
                      loadExperiments(page + 1, statusFilter, search);
                    }}
                    className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 disabled:opacity-40 disabled:pointer-events-none text-slate-300 border border-slate-700"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        </main>
      </div>

      {/* Start Experiment Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden flex flex-col">
            <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60">
              <div className="flex items-center gap-2">
                <div className="p-1.5 rounded-lg bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
                    />
                  </svg>
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">Start Evaluation Experiment</h3>
                  <p className="text-xs text-slate-400">Run test cases through an approved agent version</p>
                </div>
              </div>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white p-1 rounded-lg hover:bg-slate-800 transition-colors"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateExperiment} className="p-6 space-y-4">
              {submitError && (
                <div className="p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-300">
                  {submitError}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Experiment Name *
                </label>
                <input
                  type="text"
                  required
                  value={expName}
                  onChange={(e) => setExpName(e.target.value)}
                  placeholder="e.g. Support Agent V2 - Benchmark"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-300 mb-1">
                  Description (optional)
                </label>
                <input
                  type="text"
                  value={expDesc}
                  onChange={(e) => setExpDesc(e.target.value)}
                  placeholder="e.g. Testing improved prompt with 30-day return policy fixes"
                  className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                />
              </div>

              {loadingOptions ? (
                <div className="py-4 text-center text-xs text-slate-400">
                  Loading datasets and approved agents...
                </div>
              ) : (
                <>
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Target Dataset *
                    </label>
                    {datasets.length === 0 ? (
                      <div className="p-3 bg-amber-500/10 border border-amber-500/20 rounded-lg text-xs text-amber-300">
                        No datasets found. Please{" "}
                        <Link href="/datasets" className="underline font-bold">
                          create or upload a dataset
                        </Link>{" "}
                        first.
                      </div>
                    ) : (
                      <select
                        value={selectedDatasetId}
                        onChange={(e) => setSelectedDatasetId(e.target.value)}
                        className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                      >
                        {datasets.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name} ({d.test_cases_count} cases)
                          </option>
                        ))}
                      </select>
                    )}
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Approved Agent Adapter *
                    </label>
                    <select
                      value={selectedAgentIndex}
                      onChange={(e) => setSelectedAgentIndex(Number(e.target.value))}
                      className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
                    >
                      {agents.map((ag, idx) => (
                        <option key={`${ag.agent_name}-${ag.agent_version}`} value={idx}>
                          {ag.agent_name} (v{ag.agent_version}) — {ag.description}
                        </option>
                      ))}
                    </select>
                    {agents[selectedAgentIndex] && (
                      <p className="mt-1 text-[11px] text-slate-400 bg-slate-950/60 p-2 rounded border border-slate-800/60">
                        {agents[selectedAgentIndex].description}
                      </p>
                    )}
                  </div>
                </>
              )}

              <div className="p-3 bg-indigo-950/20 border border-indigo-900/30 rounded-lg text-[11px] text-indigo-300 space-y-1">
                <span className="font-semibold block">Execution Pipeline:</span>
                <p className="text-slate-400">
                  Runs each test case through the agent runner, captures input/output traces, and evaluates results with keyword checks, regex, JSON syntax, and latency threshold rules.
                </p>
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting || datasets.length === 0}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white flex items-center gap-2 shadow-lg shadow-indigo-500/25 transition-all"
                >
                  {submitting ? (
                    <>
                      <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      Executing...
                    </>
                  ) : (
                    "Launch Experiment"
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
