"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React, { Suspense, useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import {
  compareSafetyCampaigns,
  fetchSafetyCampaigns,
} from "@/lib/api";
import {
  SafetyCampaignSummary,
  SafetyComparison,
} from "@/lib/types";

function SafetyCompareContent() {
  const searchParams = useSearchParams();
  const initA = searchParams.get("a") || searchParams.get("baseline") || "";
  const initB = searchParams.get("b") || searchParams.get("candidate") || "";

  const [campaigns, setCampaigns] = useState<SafetyCampaignSummary[]>([]);
  const [baselineId, setBaselineId] = useState(initA);
  const [candidateId, setCandidateId] = useState(initB);

  const [comparison, setComparison] = useState<SafetyComparison | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Tab filter: newly_introduced, resolved, unchanged, all
  const [activeTab, setActiveTab] = useState<"newly_introduced" | "resolved" | "unchanged" | "all">("newly_introduced");

  // Load completed campaigns for selector
  useEffect(() => {
    fetchSafetyCampaigns({ status: "completed", pageSize: 50 })
      .then((res) => {
        setCampaigns(res.items);
        if (!baselineId && res.items.length >= 2) {
          setBaselineId(res.items[1].id);
        }
        if (!candidateId && res.items.length >= 1) {
          setCandidateId(res.items[0].id);
        }
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const runComparison = (a = baselineId, b = candidateId) => {
    if (!a || !b) return;
    if (a === b) {
      setError("Please select two distinct campaigns to compare.");
      return;
    }

    setLoading(true);
    setError(null);
    compareSafetyCampaigns(a, b)
      .then((res) => {
        setComparison(res);
        // If no newly introduced failures, switch to resolved or all
        if (res.newly_introduced_failures.length === 0 && res.resolved_failures.length > 0) {
          setActiveTab("resolved");
        } else if (res.newly_introduced_failures.length === 0 && res.resolved_failures.length === 0) {
          setActiveTab("all");
        } else {
          setActiveTab("newly_introduced");
        }
      })
      .catch((err) => setError(err.message || "Failed to compare safety campaigns."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    if (baselineId && candidateId && baselineId !== candidateId) {
      runComparison(baselineId, candidateId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [baselineId, candidateId]);

  const activeCases = !comparison
    ? []
    : activeTab === "newly_introduced"
    ? comparison.newly_introduced_failures
    : activeTab === "resolved"
    ? comparison.resolved_failures
    : activeTab === "unchanged"
    ? comparison.unchanged_failures
    : comparison.all_cases;

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
                <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider bg-rose-500/10 text-rose-400 border border-rose-500/30">
                  Regression Diff
                </span>
                <span className="text-xs text-slate-400 font-mono">Safety Comparison</span>
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-white mt-1">
                Version Regression Comparison
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Align adversarial test cases between baseline and candidate agent models to isolate newly introduced vulnerabilities.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <Link
                href="/safety/campaigns"
                className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition"
              >
                Back to Campaigns
              </Link>
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
              className="px-4 py-2 font-medium text-slate-400 hover:text-slate-200 transition"
            >
              <span>Campaigns</span>
            </Link>
            <Link
              href="/safety/compare"
              className="px-4 py-2 font-medium text-emerald-400 border-b-2 border-emerald-400 flex items-center space-x-2"
            >
              <span>Regression Compare</span>
            </Link>
          </div>

          {/* Campaign Selector Panel */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 bg-slate-900/60 p-5 rounded-xl border border-slate-800">
            {/* Baseline Campaign (A) */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Baseline Campaign (A)
              </label>
              <select
                value={baselineId}
                onChange={(e) => setBaselineId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="">Select baseline campaign...</option>
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} — {c.agent_name} ({c.agent_version}) [Pass: {c.safety_pass_rate ? `${(c.safety_pass_rate * 100).toFixed(0)}%` : "—"}]
                  </option>
                ))}
              </select>
            </div>

            {/* Candidate Campaign (B) */}
            <div className="space-y-1.5">
              <label className="block text-xs font-semibold text-slate-300 uppercase tracking-wider">
                Candidate Campaign (B)
              </label>
              <select
                value={candidateId}
                onChange={(e) => setCandidateId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
              >
                <option value="">Select candidate campaign...</option>
                {campaigns.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} — {c.agent_name} ({c.agent_version}) [Pass: {c.safety_pass_rate ? `${(c.safety_pass_rate * 100).toFixed(0)}%` : "—"}]
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Error */}
          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-sm">
              {error}
            </div>
          )}

          {/* Loading */}
          {loading && (
            <div className="p-12 text-center text-slate-400">
              <div className="inline-block animate-spin h-6 w-6 border-2 border-emerald-400 border-t-transparent rounded-full mr-2" />
              Aligning test cases and computing safety regressions...
            </div>
          )}

          {/* Comparison Content */}
          {comparison && !loading && (
            <>
              {/* Delta KPI Cards */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                {/* Delta Pass Rate */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-sm">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Delta Pass Rate
                  </span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span
                      className={`text-3xl font-extrabold ${
                        comparison.summary.delta_pass_rate > 0
                          ? "text-emerald-400"
                          : comparison.summary.delta_pass_rate < 0
                          ? "text-rose-400"
                          : "text-slate-300"
                      }`}
                    >
                      {comparison.summary.delta_pass_rate > 0 ? "+" : ""}
                      {(comparison.summary.delta_pass_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {(comparison.baseline_campaign.safety_pass_rate * 100).toFixed(1)}% (A) →{" "}
                    {(comparison.candidate_campaign.safety_pass_rate * 100).toFixed(1)}% (B)
                  </p>
                </div>

                {/* Newly Introduced Failures */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-sm">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Newly Introduced Failures
                  </span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span
                      className={`text-3xl font-extrabold ${
                        comparison.summary.newly_introduced_failures_count > 0
                          ? "text-rose-400"
                          : "text-emerald-400"
                      }`}
                    >
                      {comparison.summary.newly_introduced_failures_count}
                    </span>
                    <span
                      className={`text-xs px-2 py-0.5 rounded font-semibold ${
                        comparison.summary.newly_introduced_failures_count > 0
                          ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                          : "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                      }`}
                    >
                      {comparison.summary.newly_introduced_failures_count > 0 ? "Regressions" : "Zero Regressions"}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Passed in baseline, failed in candidate</p>
                </div>

                {/* Resolved Failures */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-sm">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Resolved Failures
                  </span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span className="text-3xl font-extrabold text-emerald-400">
                      {comparison.summary.resolved_failures_count}
                    </span>
                    <span className="text-xs px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/30 font-semibold">
                      Hardened
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">Failed in baseline, passed in candidate</p>
                </div>

                {/* Delta Critical Breaches */}
                <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-sm">
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Delta Critical Breaches
                  </span>
                  <div className="mt-2 flex items-baseline gap-2">
                    <span
                      className={`text-3xl font-extrabold ${
                        comparison.summary.delta_critical_failures < 0
                          ? "text-emerald-400"
                          : comparison.summary.delta_critical_failures > 0
                          ? "text-rose-400"
                          : "text-slate-300"
                      }`}
                    >
                      {comparison.summary.delta_critical_failures > 0 ? "+" : ""}
                      {comparison.summary.delta_critical_failures}
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1">
                    {comparison.baseline_campaign.critical_failures} in baseline → {comparison.candidate_campaign.critical_failures} in candidate
                  </p>
                </div>
              </div>

              {/* Category-by-Category Diff Table */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">Threat Category Deltas</h3>
                  <span className="text-xs text-slate-400 font-mono">
                    Baseline: {comparison.baseline_campaign.agent_version} vs Candidate: {comparison.candidate_campaign.agent_version}
                  </span>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-950/80 uppercase text-[10px] text-slate-400 border-b border-slate-800 tracking-wider">
                      <tr>
                        <th className="px-5 py-3">Threat Category</th>
                        <th className="px-5 py-3">Baseline Pass Rate</th>
                        <th className="px-5 py-3">Candidate Pass Rate</th>
                        <th className="px-5 py-3">Delta</th>
                        <th className="px-5 py-3">Failures (Base → Cand)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 font-sans">
                      {comparison.category_comparison.map((cat) => {
                        const delta = cat.delta_pass_rate * 100;
                        return (
                          <tr key={cat.category} className="hover:bg-slate-800/40 transition">
                            <td className="px-5 py-3 font-medium text-white capitalize">
                              {cat.category.replace(/_/g, " ")}
                            </td>
                            <td className="px-5 py-3 font-mono">
                              {(cat.baseline_pass_rate * 100).toFixed(1)}%
                            </td>
                            <td className="px-5 py-3 font-mono">
                              {(cat.candidate_pass_rate * 100).toFixed(1)}%
                            </td>
                            <td className="px-5 py-3">
                              <span
                                className={`font-mono font-semibold ${
                                  delta > 0
                                    ? "text-emerald-400"
                                    : delta < 0
                                    ? "text-rose-400"
                                    : "text-slate-400"
                                }`}
                              >
                                {delta > 0 ? "+" : ""}
                                {delta.toFixed(1)}%
                              </span>
                            </td>
                            <td className="px-5 py-3 font-mono text-slate-400">
                              {cat.baseline_failed} → {cat.candidate_failed}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Breakdown by Alignment Status */}
              <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm space-y-4">
                {/* Tabs */}
                <div className="flex border-b border-slate-800 text-xs">
                  <button
                    onClick={() => setActiveTab("newly_introduced")}
                    className={`px-5 py-3 font-semibold transition flex items-center space-x-1.5 ${
                      activeTab === "newly_introduced"
                        ? "text-rose-400 border-b-2 border-rose-400 bg-rose-500/5"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <span>Newly Introduced Failures</span>
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-rose-500/20 text-rose-300 font-mono">
                      {comparison.summary.newly_introduced_failures_count}
                    </span>
                  </button>

                  <button
                    onClick={() => setActiveTab("resolved")}
                    className={`px-5 py-3 font-semibold transition flex items-center space-x-1.5 ${
                      activeTab === "resolved"
                        ? "text-emerald-400 border-b-2 border-emerald-400 bg-emerald-500/5"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <span>Resolved Failures</span>
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-emerald-500/20 text-emerald-300 font-mono">
                      {comparison.summary.resolved_failures_count}
                    </span>
                  </button>

                  <button
                    onClick={() => setActiveTab("unchanged")}
                    className={`px-5 py-3 font-semibold transition flex items-center space-x-1.5 ${
                      activeTab === "unchanged"
                        ? "text-amber-400 border-b-2 border-amber-400 bg-amber-500/5"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <span>Persistent Failures</span>
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-300 font-mono">
                      {comparison.summary.unchanged_failures_count}
                    </span>
                  </button>

                  <button
                    onClick={() => setActiveTab("all")}
                    className={`px-5 py-3 font-semibold transition flex items-center space-x-1.5 ${
                      activeTab === "all"
                        ? "text-indigo-400 border-b-2 border-indigo-400 bg-indigo-500/5"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    <span>All Aligned Cases</span>
                    <span className="px-1.5 py-0.2 rounded-full text-[10px] bg-slate-800 text-slate-300 font-mono">
                      {comparison.summary.total_aligned_cases}
                    </span>
                  </button>
                </div>

                {/* Case Items List */}
                <div className="p-5 space-y-4">
                  {activeCases.length === 0 && (
                    <div className="py-8 text-center text-slate-500 text-xs">
                      No test cases in this classification category.
                    </div>
                  )}

                  {activeCases.map((c) => (
                    <div
                      key={c.stable_case_id}
                      className="p-4 bg-slate-950 border border-slate-800/80 rounded-xl space-y-3"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center space-x-2">
                          <span className="font-mono text-sm font-bold text-white">
                            {c.stable_case_id}
                          </span>
                          <span className="px-2 py-0.5 rounded text-[10px] font-semibold uppercase bg-slate-800 text-slate-300 border border-slate-700">
                            {c.category}
                          </span>
                          <span
                            className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                              c.severity === "critical"
                                ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                                : c.severity === "high"
                                ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                                : "bg-slate-800 text-slate-400"
                            }`}
                          >
                            {c.severity}
                          </span>
                        </div>

                        <span
                          className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            c.comparison_status === "newly_introduced_failure"
                              ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                              : c.comparison_status === "resolved_failure"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                              : c.comparison_status === "unchanged_failure"
                              ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                              : "bg-slate-800 text-slate-300 border border-slate-700"
                          }`}
                        >
                          {c.comparison_status.replace(/_/g, " ").toUpperCase()}
                        </span>
                      </div>

                      {/* Adversarial Attack Input */}
                      <div className="space-y-1">
                        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                          Adversarial Input
                        </span>
                        <pre className="p-2.5 bg-slate-900/80 border border-slate-800 rounded text-xs text-slate-200 overflow-x-auto whitespace-pre-wrap font-mono">
                          {typeof c.adversarial_input === "object"
                            ? JSON.stringify(c.adversarial_input, null, 2)
                            : String(c.adversarial_input)}
                        </pre>
                      </div>

                      {/* Side by side Baseline vs Candidate */}
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-slate-800/80">
                        {/* Baseline */}
                        <div className="p-3 bg-slate-900/50 border border-slate-800/80 rounded-lg space-y-1.5">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-slate-300">Baseline (A)</span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                c.baseline?.status === "pass"
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : "bg-rose-500/10 text-rose-400"
                              }`}
                            >
                              {c.baseline?.status || "MISSING"}
                            </span>
                          </div>
                          {c.baseline?.evidence && (
                            <pre className="p-2 bg-slate-950 text-[11px] text-slate-400 rounded overflow-x-auto font-mono max-h-24">
                              {typeof c.baseline.evidence === "object"
                                ? JSON.stringify(c.baseline.evidence)
                                : String(c.baseline.evidence)}
                            </pre>
                          )}
                        </div>

                        {/* Candidate */}
                        <div className="p-3 bg-slate-900/50 border border-slate-800/80 rounded-lg space-y-1.5">
                          <div className="flex items-center justify-between text-xs">
                            <span className="font-semibold text-slate-300">Candidate (B)</span>
                            <span
                              className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                c.candidate?.status === "pass"
                                  ? "bg-emerald-500/10 text-emerald-400"
                                  : "bg-rose-500/10 text-rose-400"
                              }`}
                            >
                              {c.candidate?.status || "MISSING"}
                            </span>
                          </div>
                          {c.candidate?.evidence && (
                            <pre className="p-2 bg-slate-950 text-[11px] text-slate-400 rounded overflow-x-auto font-mono max-h-24">
                              {typeof c.candidate.evidence === "object"
                                ? JSON.stringify(c.candidate.evidence)
                                : String(c.candidate.evidence)}
                            </pre>
                          )}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}

export default function SafetyComparePage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-screen bg-slate-950 text-slate-100 antialiased overflow-hidden">
          <Sidebar />
          <div className="flex-1 flex flex-col min-w-0">
            <Navbar />
            <div className="p-12 text-center text-slate-400 text-xs">
              Loading regression comparison engine...
            </div>
          </div>
        </div>
      }
    >
      <SafetyCompareContent />
    </Suspense>
  );
}
