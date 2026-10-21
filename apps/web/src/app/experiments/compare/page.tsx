"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React, { Suspense, useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { compareExperiments, fetchExperiments } from "@/lib/api";
import {
  ComparedCaseItem,
  ExperimentComparison,
  ExperimentSummary,
} from "@/lib/types";

function CompareContent() {
  const searchParams = useSearchParams();
  const initialA = searchParams?.get("a") || "";
  const initialB = searchParams?.get("b") || "";

  const [experiments, setExperiments] = useState<ExperimentSummary[]>([]);
  const [selectedA, setSelectedA] = useState<string>(initialA);
  const [selectedB, setSelectedB] = useState<string>(initialB);
  const [loadingList, setLoadingList] = useState(true);

  const [comparison, setComparison] = useState<ExperimentComparison | null>(null);
  const [comparing, setComparing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<
    "all" | "regressions" | "improvements" | "unchanged" | "errors"
  >("regressions");
  const [searchFilter, setSearchFilter] = useState("");

  // Load completed experiments for the dropdowns
  useEffect(() => {
    fetchExperiments({ pageSize: 50 })
      .then((res) => {
        setExperiments(res.items);
        if (!selectedA && res.items.length > 0) {
          setSelectedA(res.items[0].id);
        }
        if (!selectedB && res.items.length > 1) {
          setSelectedB(res.items[1].id);
        }
      })
      .catch((err) => console.error("Failed to load experiments for selector", err))
      .finally(() => setLoadingList(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runComparison = (aId = selectedA, bId = selectedB) => {
    if (!aId || !bId) {
      setError("Please select both a baseline and a candidate experiment.");
      return;
    }
    if (aId === bId) {
      setError("Please select two different experiments to compare.");
      return;
    }
    setComparing(true);
    setError(null);
    compareExperiments(aId, bId)
      .then((data) => {
        setComparison(data);
        // If there are regressions, default tab to regressions, otherwise all
        if (data.summary.regressions_count > 0) {
          setActiveTab("regressions");
        } else {
          setActiveTab("all");
        }
      })
      .catch((err) => setError(err.message || "Failed to compare experiments."))
      .finally(() => setComparing(false));
  };

  // Run automatically if initialA and initialB were passed via URL
  useEffect(() => {
    if (initialA && initialB && initialA !== initialB) {
      runComparison(initialA, initialB);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [initialA, initialB]);

  const getFilteredCases = (): ComparedCaseItem[] => {
    if (!comparison) return [];
    let items: ComparedCaseItem[] = [];
    switch (activeTab) {
      case "regressions":
        items = comparison.regressions;
        break;
      case "improvements":
        items = comparison.improvements;
        break;
      case "unchanged":
        items = comparison.unchanged;
        break;
      case "errors":
        items = comparison.errors;
        break;
      default:
        items = comparison.all_cases;
        break;
    }

    if (searchFilter.trim()) {
      const q = searchFilter.toLowerCase();
      items = items.filter((item) => {
        const inputStr = typeof item.input === "string" ? item.input : JSON.stringify(item.input || "");
        const aOutput = item.a ? JSON.stringify(item.a.actual_output || "") : "";
        const bOutput = item.b ? JSON.stringify(item.b.actual_output || "") : "";
        return inputStr.toLowerCase().includes(q) || aOutput.toLowerCase().includes(q) || bOutput.toLowerCase().includes(q);
      });
    }

    return items;
  };

  const getCategoryBadge = (category: string) => {
    switch (category) {
      case "regression":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-rose-500/20 text-rose-400 border border-rose-500/30">
            <span>🚨</span> REGRESSION
          </span>
        );
      case "improvement":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
            <span>✨</span> IMPROVEMENT
          </span>
        );
      case "error":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-amber-500/20 text-amber-400 border border-amber-500/30">
            <span>⚠️</span> EVAL ERROR
          </span>
        );
      case "missing":
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-500/20 text-slate-400 border border-slate-500/30">
            MISSING
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-bold bg-slate-800 text-slate-300 border border-slate-700">
            UNCHANGED
          </span>
        );
    }
  };

  const displayedCases = getFilteredCases();

  return (
    <main className="flex-1 p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-slate-800/80">
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-white">
              Experiment Regression Comparison
            </h1>
            <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 bg-rose-500/10 text-rose-400 border border-rose-500/20 rounded">
              Diff Engine
            </span>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            Compare candidate agent behavior against a baseline experiment to isolate regressions and improvements.
          </p>
        </div>

        <Link
          href="/experiments"
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs text-slate-300 hover:text-white bg-slate-800/80 hover:bg-slate-700 rounded-lg border border-slate-700 transition-colors"
        >
          ← Back to Experiments
        </Link>
      </div>

      {/* Selectors Bar */}
      <div className="bg-slate-900/70 border border-slate-800/80 rounded-2xl p-5 shadow-xl">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-4 items-end">
          {/* Baseline selector */}
          <div className="md:col-span-5 space-y-1.5">
            <label className="block text-xs font-bold text-slate-300 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-slate-400"></span>
              Baseline Experiment (A)
            </label>
            <select
              value={selectedA}
              onChange={(e) => setSelectedA(e.target.value)}
              disabled={loadingList || comparing}
              className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
            >
              {experiments.map((exp) => (
                <option key={exp.id} value={exp.id}>
                  {exp.name} — {exp.agent_name} v{exp.agent_version} (
                  {exp.pass_rate !== null ? `${Math.round(exp.pass_rate * 100)}%` : "no rate"})
                </option>
              ))}
            </select>
          </div>

          {/* VS Divider */}
          <div className="hidden md:flex md:col-span-1 items-center justify-center pb-2">
            <span className="text-xs font-black uppercase text-indigo-400 bg-indigo-950/60 px-2 py-1 rounded border border-indigo-900/60">
              VS
            </span>
          </div>

          {/* Candidate selector */}
          <div className="md:col-span-4 space-y-1.5">
            <label className="block text-xs font-bold text-slate-300 flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-indigo-500"></span>
              Candidate Experiment (B)
            </label>
            <select
              value={selectedB}
              onChange={(e) => setSelectedB(e.target.value)}
              disabled={loadingList || comparing}
              className="w-full px-3 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-white focus:outline-none focus:border-indigo-500"
            >
              {experiments.map((exp) => (
                <option key={exp.id} value={exp.id}>
                  {exp.name} — {exp.agent_name} v{exp.agent_version} (
                  {exp.pass_rate !== null ? `${Math.round(exp.pass_rate * 100)}%` : "no rate"})
                </option>
              ))}
            </select>
          </div>

          {/* Compare Button */}
          <div className="md:col-span-2">
            <button
              onClick={() => runComparison()}
              disabled={comparing || !selectedA || !selectedB}
              className="w-full py-2 px-4 rounded-lg bg-gradient-to-r from-indigo-500 to-indigo-600 hover:from-indigo-400 hover:to-indigo-500 text-white font-semibold text-xs shadow-lg shadow-indigo-500/25 disabled:opacity-50 flex items-center justify-center gap-2 transition-all"
            >
              {comparing ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                  Analyzing...
                </>
              ) : (
                "Run Comparison"
              )}
            </button>
          </div>
        </div>

        {error && (
          <div className="mt-4 p-3 bg-rose-500/10 border border-rose-500/20 rounded-lg text-xs text-rose-300">
            {error}
          </div>
        )}
      </div>

      {/* Comparison Results */}
      {comparison && (
        <div className="space-y-6">
          {/* Summary Banner */}
          <div className="bg-slate-900/60 border border-slate-800/80 rounded-2xl p-6 shadow-xl">
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6 items-center">
              {/* Delta KPI */}
              <div className="md:col-span-1 border-b md:border-b-0 md:border-r border-slate-800 pb-4 md:pb-0 pr-0 md:pr-4">
                <span className="text-[11px] text-slate-400 uppercase font-semibold tracking-wider">
                  Pass Rate Delta
                </span>
                <div
                  className={`text-3xl font-extrabold mt-1 flex items-center gap-1.5 ${
                    comparison.summary.pass_rate_delta > 0
                      ? "text-emerald-400"
                      : comparison.summary.pass_rate_delta < 0
                      ? "text-rose-400"
                      : "text-slate-300"
                  }`}
                >
                  {comparison.summary.pass_rate_delta > 0 ? "+" : ""}
                  {(comparison.summary.pass_rate_delta * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-slate-500 mt-1">
                  Score delta: {comparison.summary.score_delta >= 0 ? "+" : ""}
                  {comparison.summary.score_delta.toFixed(2)}
                </div>
              </div>

              {/* Experiments Quick Info */}
              <div className="md:col-span-3 grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/80">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-slate-400">Baseline (A):</span>
                    <span className="text-slate-200">{comparison.experiment_a.name}</span>
                  </div>
                  <div className="text-xs text-slate-400 mt-1 font-mono">
                    {comparison.experiment_a.agent_name} v{comparison.experiment_a.agent_version}
                  </div>
                  <div className="mt-2 text-xs flex justify-between">
                    <span className="text-slate-500">Pass Rate:</span>
                    <span className="font-semibold text-slate-300">
                      {comparison.experiment_a.pass_rate !== null
                        ? `${Math.round(comparison.experiment_a.pass_rate * 100)}%`
                        : "—"}
                    </span>
                  </div>
                </div>

                <div className="bg-indigo-950/20 p-3 rounded-xl border border-indigo-900/30">
                  <div className="flex items-center justify-between text-xs font-semibold">
                    <span className="text-indigo-400">Candidate (B):</span>
                    <span className="text-white">{comparison.experiment_b.name}</span>
                  </div>
                  <div className="text-xs text-indigo-300 mt-1 font-mono">
                    {comparison.experiment_b.agent_name} v{comparison.experiment_b.agent_version}
                  </div>
                  <div className="mt-2 text-xs flex justify-between">
                    <span className="text-slate-500">Pass Rate:</span>
                    <span className="font-semibold text-white">
                      {comparison.experiment_b.pass_rate !== null
                        ? `${Math.round(comparison.experiment_b.pass_rate * 100)}%`
                        : "—"}
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Metric counters */}
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-6 pt-6 border-t border-slate-800/60">
              <div
                onClick={() => setActiveTab("regressions")}
                className={`cursor-pointer p-3 rounded-xl border transition-all ${
                  activeTab === "regressions"
                    ? "bg-rose-500/20 border-rose-500/50 shadow-lg shadow-rose-500/10"
                    : "bg-rose-950/10 border-rose-900/20 hover:border-rose-800/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-rose-400">Regressions</span>
                  <span>🚨</span>
                </div>
                <div className="text-2xl font-black text-rose-300 mt-1 font-mono">
                  {comparison.summary.regressions_count}
                </div>
                <span className="text-[10px] text-slate-500">Passed in A, Failed in B</span>
              </div>

              <div
                onClick={() => setActiveTab("improvements")}
                className={`cursor-pointer p-3 rounded-xl border transition-all ${
                  activeTab === "improvements"
                    ? "bg-emerald-500/20 border-emerald-500/50 shadow-lg shadow-emerald-500/10"
                    : "bg-emerald-950/10 border-emerald-900/20 hover:border-emerald-800/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-emerald-400">Improvements</span>
                  <span>✨</span>
                </div>
                <div className="text-2xl font-black text-emerald-300 mt-1 font-mono">
                  {comparison.summary.improvements_count}
                </div>
                <span className="text-[10px] text-slate-500">Failed in A, Passed in B</span>
              </div>

              <div
                onClick={() => setActiveTab("unchanged")}
                className={`cursor-pointer p-3 rounded-xl border transition-all ${
                  activeTab === "unchanged"
                    ? "bg-slate-800/60 border-slate-600 shadow-md"
                    : "bg-slate-950/40 border-slate-800/40 hover:border-slate-700/60"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-slate-300">Unchanged</span>
                  <span>🤝</span>
                </div>
                <div className="text-2xl font-black text-slate-300 mt-1 font-mono">
                  {comparison.summary.unchanged_count}
                </div>
                <span className="text-[10px] text-slate-500">Identical outcomes</span>
              </div>

              <div
                onClick={() => setActiveTab("errors")}
                className={`cursor-pointer p-3 rounded-xl border transition-all ${
                  activeTab === "errors"
                    ? "bg-amber-500/20 border-amber-500/50 shadow-md"
                    : "bg-amber-950/10 border-amber-900/20 hover:border-amber-800/40"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-amber-400">Errors</span>
                  <span>⚠️</span>
                </div>
                <div className="text-2xl font-black text-amber-300 mt-1 font-mono">
                  {comparison.summary.errors_count}
                </div>
                <span className="text-[10px] text-slate-500">Execution errors</span>
              </div>

              <div
                onClick={() => setActiveTab("all")}
                className={`cursor-pointer p-3 rounded-xl border transition-all ${
                  activeTab === "all"
                    ? "bg-indigo-500/20 border-indigo-500/50 shadow-md"
                    : "bg-slate-950/40 border-slate-800/40 hover:border-slate-700/60"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[11px] font-bold text-indigo-300">Total Cases</span>
                  <span>📋</span>
                </div>
                <div className="text-2xl font-black text-white mt-1 font-mono">
                  {comparison.summary.total_compared}
                </div>
                <span className="text-[10px] text-slate-500">All aligned cases</span>
              </div>
            </div>
          </div>

          {/* Filter Bar */}
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
                placeholder="Search compared case input or outputs..."
                value={searchFilter}
                onChange={(e) => setSearchFilter(e.target.value)}
                className="w-full pl-9 pr-3 py-1.5 text-xs bg-slate-950/80 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500"
              />
            </div>

            <div className="flex items-center gap-2 overflow-x-auto w-full sm:w-auto">
              {(
                [
                  ["regressions", `Regressions (${comparison.summary.regressions_count})`],
                  ["improvements", `Improvements (${comparison.summary.improvements_count})`],
                  ["unchanged", `Unchanged (${comparison.summary.unchanged_count})`],
                  ["errors", `Errors (${comparison.summary.errors_count})`],
                  ["all", `All (${comparison.summary.total_compared})`],
                ] as const
              ).map(([tabKey, label]) => (
                <button
                  key={tabKey}
                  onClick={() => setActiveTab(tabKey)}
                  className={`px-3 py-1 text-xs rounded-lg font-medium transition-colors whitespace-nowrap ${
                    activeTab === tabKey
                      ? "bg-indigo-600 text-white shadow-sm"
                      : "bg-slate-900/80 text-slate-400 hover:text-slate-200 hover:bg-slate-800 border border-slate-800/80"
                  }`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Cases List */}
          {displayedCases.length === 0 ? (
            <div className="py-12 text-center bg-slate-900/40 border border-slate-800/60 rounded-xl">
              <p className="text-sm text-slate-400">
                {activeTab === "regressions"
                  ? "🎉 Zero regressions detected! The candidate version maintained or improved on all baseline cases."
                  : "No test cases found in this category."}
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {displayedCases.map((item, idx) => (
                <div
                  key={item.test_case_id}
                  className={`bg-slate-900/60 border rounded-2xl p-5 shadow-lg space-y-4 ${
                    item.category === "regression"
                      ? "border-rose-500/40 bg-gradient-to-b from-rose-950/10 to-slate-900/60"
                      : item.category === "improvement"
                      ? "border-emerald-500/40 bg-gradient-to-b from-emerald-950/10 to-slate-900/60"
                      : "border-slate-800/80"
                  }`}
                >
                  {/* Item Header */}
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 pb-3 border-b border-slate-800/60">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                        Case #{idx + 1}
                      </span>
                      {getCategoryBadge(item.category)}
                    </div>
                    <span className="font-mono text-[10px] text-slate-500 truncate max-w-xs">
                      ID: {item.test_case_id}
                    </span>
                  </div>

                  {/* Input & Expected */}
                  <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800/60 text-xs space-y-2">
                    <div>
                      <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">
                        Test Input
                      </span>
                      <p className="font-mono text-slate-200 mt-0.5 break-words">
                        {typeof item.input === "string" ? item.input : JSON.stringify(item.input)}
                      </p>
                    </div>
                    {item.expected_output && (
                      <div className="pt-2 border-t border-slate-800/60">
                        <span className="text-[10px] text-slate-500 uppercase font-bold tracking-wider">
                          Expected Output / Criteria
                        </span>
                        <p className="font-mono text-slate-300 mt-0.5 break-words">
                          {typeof item.expected_output === "string"
                            ? item.expected_output
                            : JSON.stringify(item.expected_output)}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Side-by-Side Outputs */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Baseline A */}
                    <div className="bg-slate-950/50 p-4 rounded-xl border border-slate-800/80 space-y-2">
                      <div className="flex items-center justify-between pb-2 border-b border-slate-800/60 text-xs">
                        <span className="font-semibold text-slate-400">Baseline (A) Output</span>
                        {item.a ? (
                          <span
                            className={`font-bold uppercase text-[10px] px-2 py-0.5 rounded ${
                              item.a.status === "pass"
                                ? "bg-emerald-500/20 text-emerald-400"
                                : "bg-rose-500/20 text-rose-400"
                            }`}
                          >
                            {item.a.status} (score: {Object.values(item.a.scores)[0]?.toFixed(2) || "—"})
                          </span>
                        ) : (
                          <span className="text-slate-500 italic text-[11px]">Missing</span>
                        )}
                      </div>
                      <div className="font-mono text-xs text-slate-200 bg-slate-900/60 p-2.5 rounded border border-slate-800/60 break-words min-h-[60px]">
                        {item.a?.actual_output !== undefined
                          ? String(item.a.actual_output)
                          : "No result captured"}
                      </div>
                      {item.a?.evaluation_details && item.a.evaluation_details.length > 0 && (
                        <div className="text-[11px] text-slate-400 space-y-1 pt-1">
                          {item.a.evaluation_details.map((ev, eIdx) => (
                            <div key={eIdx} className="text-slate-400">
                              <span className="font-semibold text-slate-300">{ev.evaluator_name}: </span>
                              {ev.explanation}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Candidate B */}
                    <div
                      className={`p-4 rounded-xl border space-y-2 ${
                        item.category === "regression"
                          ? "bg-rose-950/20 border-rose-900/40"
                          : "bg-slate-950/50 border-slate-800/80"
                      }`}
                    >
                      <div className="flex items-center justify-between pb-2 border-b border-slate-800/60 text-xs">
                        <span className="font-semibold text-indigo-400">Candidate (B) Output</span>
                        {item.b ? (
                          <span
                            className={`font-bold uppercase text-[10px] px-2 py-0.5 rounded ${
                              item.b.status === "pass"
                                ? "bg-emerald-500/20 text-emerald-400"
                                : "bg-rose-500/20 text-rose-400"
                            }`}
                          >
                            {item.b.status} (score: {Object.values(item.b.scores)[0]?.toFixed(2) || "—"})
                          </span>
                        ) : (
                          <span className="text-slate-500 italic text-[11px]">Missing</span>
                        )}
                      </div>
                      <div className="font-mono text-xs text-slate-200 bg-slate-900/60 p-2.5 rounded border border-slate-800/60 break-words min-h-[60px]">
                        {item.b?.actual_output !== undefined
                          ? String(item.b.actual_output)
                          : "No result captured"}
                      </div>
                      {item.b?.evaluation_details && item.b.evaluation_details.length > 0 && (
                        <div className="text-[11px] text-slate-400 space-y-1 pt-1">
                          {item.b.evaluation_details.map((ev, eIdx) => (
                            <div key={eIdx} className="text-slate-300">
                              <span className="font-semibold text-indigo-300">{ev.evaluator_name}: </span>
                              {ev.explanation}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </main>
  );
}

export default function ExperimentsComparePage() {
  return (
    <div className="flex min-h-screen bg-[#070b14] text-slate-100 font-sans">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0">
        <Navbar />
        <Suspense
          fallback={
            <div className="p-8 text-center text-slate-400 text-xs">
              Loading comparison engine...
            </div>
          }
        >
          <CompareContent />
        </Suspense>
      </div>
    </div>
  );
}
