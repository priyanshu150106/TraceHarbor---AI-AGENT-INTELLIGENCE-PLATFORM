"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchExperimentDetail } from "@/lib/api";
import { ExperimentDetail, ExperimentResult } from "@/lib/types";

export default function ExperimentDetailPage() {
  const params = useParams();
  const experimentId = params?.id as string;

  const [experiment, setExperiment] = useState<ExperimentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [search, setSearch] = useState("");
  const [selectedResult, setSelectedResult] = useState<ExperimentResult | null>(null);
  const [expandedCases, setExpandedCases] = useState<Record<string, boolean>>({});

  const loadExperiment = React.useCallback(() => {
    if (!experimentId) return;
    setLoading(true);
    setError(null);
    fetchExperimentDetail(experimentId)
      .then((data) => {
        setExperiment(data);
      })
      .catch((err) => setError(err.message || "Failed to load experiment details."))
      .finally(() => setLoading(false));
  }, [experimentId]);

  useEffect(() => {
    loadExperiment();
  }, [loadExperiment]);

  const toggleExpand = (id: string) => {
    setExpandedCases((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const filteredResults = (experiment?.results || []).filter((res) => {
    if (statusFilter !== "all" && res.status.toLowerCase() !== statusFilter) {
      return false;
    }
    if (search.trim()) {
      const q = search.toLowerCase();
      const inputStr = typeof res.test_input === "string" ? res.test_input : JSON.stringify(res.test_input || "");
      const outputStr = typeof res.actual_output === "string" ? res.actual_output : JSON.stringify(res.actual_output || "");
      const hasExplanation = (res.evaluation_details || []).some((d) =>
        d.explanation.toLowerCase().includes(q)
      );
      if (!inputStr.toLowerCase().includes(q) && !outputStr.toLowerCase().includes(q) && !hasExplanation) {
        return false;
      }
    }
    return true;
  });

  const getStatusBadge = (status: string) => {
    switch (status.toLowerCase()) {
      case "pass":
      case "completed":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400"></span>
            PASS
          </span>
        );
      case "fail":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-rose-400"></span>
            FAIL
          </span>
        );
      case "error":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400"></span>
            ERROR
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-300 border border-slate-500/20">
            <span className="w-1.5 h-1.5 rounded-full bg-slate-400"></span>
            {status.toUpperCase()}
          </span>
        );
    }
  };

  const renderValue = (val: any) => {
    if (val === null || val === undefined) return <span className="text-slate-500 italic">None</span>;
    if (typeof val === "object") {
      return (
        <pre className="font-mono text-[11px] bg-slate-950 p-2 rounded border border-slate-800 text-indigo-300 overflow-x-auto whitespace-pre-wrap">
          {JSON.stringify(val, null, 2)}
        </pre>
      );
    }
    return <span className="text-slate-200">{String(val)}</span>;
  };

  return (
    <div className="flex min-h-screen bg-[#070b14] text-slate-100 font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar />

        <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Breadcrumb & Navigation */}
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-xs text-slate-400">
              <Link href="/experiments" className="hover:text-indigo-400 transition-colors">
                ← Experiments
              </Link>
              <span>/</span>
              <span className="text-slate-200 font-medium truncate max-w-xs">
                {experiment?.name || experimentId}
              </span>
            </div>

            {experiment && (
              <div className="flex items-center gap-2">
                <Link
                  href={`/experiments/compare?a=${experiment.id}`}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-500/20 transition-all"
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth="2"
                      d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"
                    />
                  </svg>
                  Compare with Candidate
                </Link>
                <button
                  onClick={loadExperiment}
                  title="Reload details"
                  className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition-colors"
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
            )}
          </div>

          {loading ? (
            <div className="py-24 flex flex-col items-center justify-center space-y-3">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm text-slate-400">Loading evaluation results...</span>
            </div>
          ) : error || !experiment ? (
            <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-xl">
              <p className="text-sm font-semibold text-rose-300">{error || "Experiment not found."}</p>
              <Link
                href="/experiments"
                className="inline-block mt-4 px-4 py-2 text-xs bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700"
              >
                Back to Experiments
              </Link>
            </div>
          ) : (
            <>
              {/* Header Card */}
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl relative overflow-hidden">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1.5">
                    <div className="flex items-center gap-3">
                      <h1 className="text-2xl font-bold text-white tracking-tight">
                        {experiment.name}
                      </h1>
                      {getStatusBadge(experiment.status)}
                    </div>
                    {experiment.description && (
                      <p className="text-xs text-slate-400">{experiment.description}</p>
                    )}
                    <div className="flex flex-wrap items-center gap-4 text-xs text-slate-400 pt-1">
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500">Agent:</span>
                        <span className="font-mono text-indigo-300 font-semibold bg-indigo-950/40 px-2 py-0.5 rounded border border-indigo-800/40">
                          {experiment.agent_name} v{experiment.agent_version}
                        </span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500">Dataset:</span>
                        <Link
                          href="/datasets"
                          className="text-slate-200 hover:text-indigo-400 font-medium underline"
                        >
                          {experiment.dataset_name || experiment.dataset_id}
                        </Link>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span className="text-slate-500">Date:</span>
                        <span className="text-slate-300">
                          {new Date(experiment.created_at).toLocaleString()}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Pass rate progress card */}
                  <div className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 flex items-center gap-6 self-start md:self-auto">
                    <div>
                      <div className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
                        Pass Rate
                      </div>
                      <div className="text-3xl font-extrabold text-white mt-0.5">
                        {experiment.pass_rate !== null
                          ? `${Math.round(experiment.pass_rate * 100)}%`
                          : "—"}
                      </div>
                    </div>
                    <div className="w-px h-10 bg-slate-800"></div>
                    <div>
                      <div className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
                        Mean Score
                      </div>
                      <div className="text-3xl font-extrabold text-indigo-400 mt-0.5 font-mono">
                        {experiment.score !== null ? experiment.score.toFixed(2) : "—"}
                      </div>
                    </div>
                  </div>
                </div>

                {/* KPI Metrics */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-slate-800/60">
                  <div className="bg-slate-950/40 p-3 rounded-lg border border-slate-800/40">
                    <span className="text-[11px] text-slate-400 font-medium">Total Test Cases</span>
                    <p className="text-lg font-bold text-white mt-0.5 font-mono">
                      {experiment.total_cases}
                    </p>
                  </div>
                  <div className="bg-emerald-950/20 p-3 rounded-lg border border-emerald-900/30">
                    <span className="text-[11px] text-emerald-400 font-medium">Passed Cases</span>
                    <p className="text-lg font-bold text-emerald-300 mt-0.5 font-mono">
                      {experiment.passed_cases}
                    </p>
                  </div>
                  <div className="bg-rose-950/20 p-3 rounded-lg border border-rose-900/30">
                    <span className="text-[11px] text-rose-400 font-medium">Failed Cases</span>
                    <p className="text-lg font-bold text-rose-300 mt-0.5 font-mono">
                      {experiment.failed_cases}
                    </p>
                  </div>
                  <div className="bg-amber-950/20 p-3 rounded-lg border border-amber-900/30">
                    <span className="text-[11px] text-amber-400 font-medium">Errored Cases</span>
                    <p className="text-lg font-bold text-amber-300 mt-0.5 font-mono">
                      {experiment.errored_cases}
                    </p>
                  </div>
                </div>
              </div>

              {/* Case Results List & Filter */}
              <div className="space-y-4">
                <div className="flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-900/40 p-3 rounded-xl border border-slate-800/60">
                  <div className="relative flex-1 w-full sm:max-w-md">
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
                      placeholder="Filter by input, output, or evaluator reason..."
                      value={search}
                      onChange={(e) => setSearch(e.target.value)}
                      className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
                    />
                  </div>

                  <div className="flex items-center gap-2 w-full sm:w-auto">
                    {["all", "pass", "fail", "error"].map((status) => (
                      <button
                        key={status}
                        onClick={() => setStatusFilter(status)}
                        className={`px-3 py-1 text-xs rounded-lg font-medium transition-colors uppercase ${
                          statusFilter === status
                            ? "bg-indigo-600 text-white shadow-sm"
                            : "bg-slate-900/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800/80"
                        }`}
                      >
                        {status}
                      </button>
                    ))}
                    <span className="text-xs text-slate-500 ml-2">
                      Showing {filteredResults.length} of {experiment.results.length} cases
                    </span>
                  </div>
                </div>

                {filteredResults.length === 0 ? (
                  <div className="py-12 text-center bg-slate-900/40 border border-slate-800/60 rounded-xl">
                    <p className="text-sm text-slate-400">No test cases match your filter criteria.</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {filteredResults.map((result, idx) => {
                      const isExpanded = !!expandedCases[result.id];
                      return (
                        <div
                          key={result.id}
                          className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 transition-all hover:border-slate-700/80 shadow-md"
                        >
                          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-800/60">
                            <div className="flex items-center gap-3">
                              <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                                Case #{idx + 1}
                              </span>
                              {getStatusBadge(result.status)}
                              {result.duration_ms !== null && (
                                <span className="text-[11px] text-slate-400 font-mono">
                                  {result.duration_ms.toFixed(1)}ms
                                </span>
                              )}
                            </div>

                            <div className="flex items-center gap-2">
                              {result.run_id && (
                                <Link
                                  href={`/runs/${result.run_id}`}
                                  target="_blank"
                                  className="inline-flex items-center gap-1 text-[11px] font-medium text-indigo-400 hover:text-indigo-300 bg-indigo-950/30 hover:bg-indigo-950/50 px-2.5 py-1 rounded border border-indigo-800/40 transition-colors"
                                >
                                  <span>View Trace Waterfall</span>
                                  <svg
                                    className="w-3 h-3"
                                    fill="none"
                                    stroke="currentColor"
                                    viewBox="0 0 24 24"
                                  >
                                    <path
                                      strokeLinecap="round"
                                      strokeLinejoin="round"
                                      strokeWidth="2"
                                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                                    />
                                  </svg>
                                </Link>
                              )}
                              <button
                                onClick={() => toggleExpand(result.id)}
                                className="text-[11px] text-slate-400 hover:text-slate-200 px-2 py-1 rounded bg-slate-800/60 hover:bg-slate-800 border border-slate-700/60 transition-colors"
                              >
                                {isExpanded ? "Collapse" : "Expand"}
                              </button>
                            </div>
                          </div>

                          {/* Primary Case Content */}
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-3 text-xs">
                            <div className="space-y-1">
                              <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
                                Input
                              </span>
                              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60 font-mono text-slate-200 break-words">
                                {typeof result.test_input === "string"
                                  ? result.test_input
                                  : JSON.stringify(result.test_input, null, 2)}
                              </div>
                            </div>

                            <div className="space-y-1">
                              <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
                                Agent Actual Output
                              </span>
                              <div className="bg-slate-950/60 p-2.5 rounded-lg border border-slate-800/60 font-mono text-slate-200 break-words">
                                {result.actual_output !== null && result.actual_output !== undefined ? (
                                  typeof result.actual_output === "string" ? (
                                    result.actual_output
                                  ) : (
                                    JSON.stringify(result.actual_output, null, 2)
                                  )
                                ) : (
                                  <span className="text-slate-500 italic">None</span>
                                )}
                              </div>
                            </div>
                          </div>

                          {/* Expected output if present */}
                          {result.expected_output && (
                            <div className="mt-3 pt-2 border-t border-slate-800/40 text-xs">
                              <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
                                Expected Output
                              </span>
                              <div className="bg-slate-950/40 p-2 rounded-lg border border-slate-800/40 text-slate-300 font-mono text-[11px] mt-1">
                                {typeof result.expected_output === "string"
                                  ? result.expected_output
                                  : JSON.stringify(result.expected_output, null, 2)}
                              </div>
                            </div>
                          )}

                          {/* Evaluators summary & explanations */}
                          {result.evaluation_details && result.evaluation_details.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-slate-800/60 space-y-2">
                              <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider block">
                                Rule Evaluator Results
                              </span>
                              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                {result.evaluation_details.map((ev, eIdx) => (
                                  <div
                                    key={eIdx}
                                    className={`p-2.5 rounded-lg border text-xs flex flex-col justify-between ${
                                      ev.outcome === "pass"
                                        ? "bg-emerald-950/10 border-emerald-900/30 text-emerald-300"
                                        : ev.outcome === "fail"
                                        ? "bg-rose-950/10 border-rose-900/30 text-rose-300"
                                        : "bg-amber-950/10 border-amber-900/30 text-amber-300"
                                    }`}
                                  >
                                    <div className="flex items-center justify-between font-mono font-semibold text-[11px] pb-1 border-b border-white/5">
                                      <span>{ev.evaluator_name}</span>
                                      <span className="uppercase text-[10px] px-1.5 py-0.2 rounded font-bold">
                                        {ev.outcome} (score: {ev.score})
                                      </span>
                                    </div>
                                    <p className="text-[11px] text-slate-300 mt-1.5">
                                      {ev.explanation}
                                    </p>
                                    {isExpanded && (
                                      <div className="mt-2 pt-2 border-t border-white/5 text-[10px] space-y-1 font-mono text-slate-400">
                                        {ev.expected_value !== null && ev.expected_value !== undefined && (
                                          <div>
                                            <span className="text-slate-500">Expected: </span>
                                            {JSON.stringify(ev.expected_value)}
                                          </div>
                                        )}
                                        {ev.actual_value !== null && ev.actual_value !== undefined && (
                                          <div>
                                            <span className="text-slate-500">Actual: </span>
                                            {JSON.stringify(ev.actual_value)}
                                          </div>
                                        )}
                                      </div>
                                    )}
                                  </div>
                                ))}
                              </div>
                            </div>
                          )}

                          {result.error && (
                            <div className="mt-3 p-2.5 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-300">
                              <span className="font-semibold">Execution Error: </span>
                              {result.error}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}
