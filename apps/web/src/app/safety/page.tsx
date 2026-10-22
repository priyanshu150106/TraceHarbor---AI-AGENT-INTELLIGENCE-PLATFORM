"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchSafetyOverview } from "@/lib/api";
import { SafetyOverview } from "@/lib/types";

const CATEGORY_LABELS: Record<string, { title: string; desc: string }> = {
  prompt_injection: {
    title: "Prompt Injection",
    desc: "Direct & indirect attempts to override instructions or hijack task boundaries",
  },
  instruction_hierarchy: {
    title: "Instruction Hierarchy",
    desc: "Untrusted user or retrieved text attempting to supersede system prompt",
  },
  sensitive_data: {
    title: "Sensitive Data Handling",
    desc: "Canary token extraction, secret leakage, and credential harvesting",
  },
  unsafe_tool_use: {
    title: "Unsafe Tool Use",
    desc: "Unauthorized, destructive, or denylisted mock tool invocation",
  },
  policy_boundary: {
    title: "Policy Boundaries",
    desc: "Attempts to elicit unauthorized claims, pricing discounts, or policy breaches",
  },
  data_exfiltration: {
    title: "Data Exfiltration",
    desc: "Egress of synthetic canary tokens through output or external URLs",
  },
  jailbreak_refusal: {
    title: "Jailbreak & Refusal",
    desc: "DAN roleplay and boundary attacks requiring explicit refusal language",
  },
};

export default function SafetyOverviewPage() {
  const [data, setData] = useState<SafetyOverview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = () => {
    setLoading(true);
    setError(null);
    fetchSafetyOverview()
      .then((res) => setData(res))
      .catch((err) => setError(err.message || "Failed to load safety overview."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData();
  }, []);

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
                  AI Red-Teaming
                </span>
                <span className="text-xs text-slate-400 font-mono">Phase 5 Production Module</span>
              </div>
              <h1 className="text-2xl lg:text-3xl font-bold tracking-tight text-white mt-1">
                AI Agent Safety & Red-Teaming
              </h1>
              <p className="text-sm text-slate-400 mt-0.5">
                Evaluate agent defenses against prompt injections, secret leakage, unauthorized tools, and policy regressions.
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
                <span>Compare Versions</span>
              </Link>

              <Link
                href="/safety/campaigns"
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg shadow-sm transition flex items-center space-x-2"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>New Safety Campaign</span>
              </Link>
            </div>
          </div>

          {/* Sub Navigation Bar */}
          <div className="flex items-center space-x-1 border-b border-slate-800 text-sm">
            <Link
              href="/safety"
              className="px-4 py-2 font-medium text-emerald-400 border-b-2 border-emerald-400 flex items-center space-x-2"
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
              className="px-4 py-2 font-medium text-slate-400 hover:text-slate-200 transition"
            >
              <span>Regression Compare</span>
            </Link>
          </div>

          {/* Error Message */}
          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-sm flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <svg className="w-5 h-5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{error}</span>
              </div>
              <button onClick={loadData} className="text-xs underline hover:no-underline font-medium">
                Retry
              </button>
            </div>
          )}

          {/* Loading State */}
          {loading && !data && (
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4 animate-pulse">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-28 bg-slate-900/60 rounded-xl border border-slate-800/80 p-5" />
              ))}
            </div>
          )}

          {/* Operational Metrics Cards */}
          {data && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Overall Pass Rate */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Safety Pass Rate
                  </span>
                  <div className="h-8 w-8 rounded-lg bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-white">
                    {data.overall_safety_pass_rate !== null
                      ? `${(data.overall_safety_pass_rate * 100).toFixed(1)}%`
                      : "—"}
                  </span>
                  {data.overall_safety_pass_rate !== null && (
                    <span
                      className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                        data.overall_safety_pass_rate >= 0.9
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                          : data.overall_safety_pass_rate >= 0.7
                          ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                          : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                      }`}
                    >
                      {data.overall_safety_pass_rate >= 0.9 ? "Strong" : data.overall_safety_pass_rate >= 0.7 ? "At Risk" : "Critical"}
                    </span>
                  )}
                </div>
                <p className="text-xs text-slate-500 mt-1">Weighted across completed benchmarks</p>
              </div>

              {/* Critical Failures */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Critical Failures
                  </span>
                  <div className="h-8 w-8 rounded-lg bg-rose-500/10 border border-rose-500/20 flex items-center justify-center text-rose-400">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-white">
                    {data.total_critical_failures}
                  </span>
                  <span
                    className={`text-xs px-2 py-0.5 rounded-md font-medium ${
                      data.total_critical_failures === 0
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                        : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                    }`}
                  >
                    {data.total_critical_failures === 0 ? "0 Breaches" : "Action Required"}
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">High-risk vulnerabilities detected</p>
              </div>

              {/* Total Campaigns */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Total Campaigns
                  </span>
                  <div className="h-8 w-8 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
                    </svg>
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-white">{data.total_campaigns}</span>
                  <span className="text-xs text-slate-400">runs</span>
                </div>
                <p className="text-xs text-slate-500 mt-1">Adversarial test campaign evaluations</p>
              </div>

              {/* Threat Categories Covered */}
              <div className="bg-slate-900/70 border border-slate-800 rounded-xl p-5 shadow-sm">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Threat Categories
                  </span>
                  <div className="h-8 w-8 rounded-lg bg-amber-500/10 border border-amber-500/20 flex items-center justify-center text-amber-400">
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
                    </svg>
                  </div>
                </div>
                <div className="mt-3 flex items-baseline gap-2">
                  <span className="text-3xl font-extrabold text-white">7 / 7</span>
                  <span className="text-xs px-2 py-0.5 rounded-md bg-amber-500/10 text-amber-400 border border-amber-500/30 font-medium">
                    Full Matrix
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-1">Injection, secrets, tools, policies</p>
              </div>
            </div>
          )}

          {/* Threat Category Breakdown Matrix */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-800 pb-3">
              <div>
                <h2 className="text-base font-semibold text-white">Adversarial Threat Categories Breakdown</h2>
                <p className="text-xs text-slate-400">
                  Deterministic pass rates across the 7 core AI agent security threat categories.
                </p>
              </div>
              <span className="text-xs text-slate-500 font-mono">Evaluation Engine v1.0</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {Object.entries(CATEGORY_LABELS).map(([catKey, info]) => {
                const stats = data?.category_breakdown?.[catKey];
                const total = stats?.total || 0;
                const passed = stats?.passed || 0;
                const failed = stats?.failed || 0;
                const rate = total > 0 ? (passed / total) * 100 : null;

                return (
                  <div
                    key={catKey}
                    className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-lg space-y-2 hover:border-slate-700 transition"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <span className="font-medium text-sm text-slate-200">{info.title}</span>
                      </div>
                      <div className="flex items-center space-x-2">
                        {rate !== null ? (
                          <span
                            className={`text-xs px-2 py-0.5 rounded font-mono font-medium ${
                              rate >= 90
                                ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                : rate >= 70
                                ? "bg-amber-500/10 text-amber-400 border border-amber-500/20"
                                : "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                            }`}
                          >
                            {rate.toFixed(1)}% Safe
                          </span>
                        ) : (
                          <span className="text-xs text-slate-500 font-mono">No Tests Yet</span>
                        )}
                      </div>
                    </div>

                    <p className="text-xs text-slate-400">{info.desc}</p>

                    {/* Progress Bar */}
                    <div className="w-full bg-slate-800/80 rounded-full h-2 overflow-hidden flex">
                      {rate !== null ? (
                        <>
                          <div
                            className="bg-emerald-500 h-2 transition-all duration-500"
                            style={{ width: `${rate}%` }}
                          />
                          <div
                            className="bg-rose-500 h-2 transition-all duration-500"
                            style={{ width: `${100 - rate}%` }}
                          />
                        </>
                      ) : (
                        <div className="bg-slate-800 h-2 w-full" />
                      )}
                    </div>

                    <div className="flex items-center justify-between text-xs text-slate-500 pt-1">
                      <span>Total Cases: {total}</span>
                      <span>
                        Passed: <strong className="text-emerald-400">{passed}</strong> | Failed:{" "}
                        <strong className="text-rose-400">{failed}</strong>
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Recent Safety Campaigns Table */}
          <div className="bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
            <div className="p-5 border-b border-slate-800 flex items-center justify-between">
              <div>
                <h3 className="text-base font-semibold text-white">Recent Safety Campaigns</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  Latest red-teaming executions, vulnerability findings, and critical breaches.
                </p>
              </div>
              <Link
                href="/safety/campaigns"
                className="text-xs text-emerald-400 hover:text-emerald-300 font-medium transition flex items-center space-x-1"
              >
                <span>View All Campaigns</span>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </Link>
            </div>

            {(!data || data.recent_campaigns.length === 0) && !loading && (
              <div className="p-12 text-center space-y-3">
                <div className="w-12 h-12 rounded-xl bg-slate-800/60 border border-slate-700/60 mx-auto flex items-center justify-center text-slate-400">
                  <svg className="w-6 h-6 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                  </svg>
                </div>
                <h4 className="text-sm font-semibold text-slate-200">No safety campaigns executed yet</h4>
                <p className="text-xs text-slate-400 max-w-sm mx-auto">
                  Run your first adversarial red-team campaign against an approved agent adapter using our curated benchmark.
                </p>
                <div className="pt-2">
                  <Link
                    href="/safety/campaigns"
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-medium rounded-lg transition inline-flex items-center space-x-1.5"
                  >
                    <span>Launch First Campaign</span>
                  </Link>
                </div>
              </div>
            )}

            {data && data.recent_campaigns.length > 0 && (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm text-slate-300">
                  <thead className="bg-slate-950/60 text-xs uppercase text-slate-400 border-b border-slate-800 tracking-wider">
                    <tr>
                      <th className="px-5 py-3">Campaign Name</th>
                      <th className="px-5 py-3">Agent & Version</th>
                      <th className="px-5 py-3">Dataset</th>
                      <th className="px-5 py-3">Safety Pass Rate</th>
                      <th className="px-5 py-3">Critical Breaches</th>
                      <th className="px-5 py-3">Status</th>
                      <th className="px-5 py-3 text-right">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 font-sans">
                    {data.recent_campaigns.map((camp) => {
                      const rate = camp.safety_pass_rate !== null && camp.safety_pass_rate !== undefined
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
                            <div className="text-xs text-slate-500">
                              {new Date(camp.created_at).toLocaleString()}
                            </div>
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
                                <span>{camp.critical_failures} Critical</span>
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
                          <td className="px-5 py-3.5 text-right">
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
            )}
          </div>
        </main>
      </div>
    </div>
  );
}
