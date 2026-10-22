"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchSafetyCampaignDetail } from "@/lib/api";
import { SafetyCampaignDetail, SafetyTestResult } from "@/lib/types";

export default function SafetyCampaignDetailPage() {
  const params = useParams();
  const id = params?.id as string;

  const [campaign, setCampaign] = useState<SafetyCampaignDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [severityFilter, setSeverityFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [search, setSearch] = useState("");

  // Drawer / inspection
  const [selectedResult, setSelectedResult] = useState<SafetyTestResult | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    fetchSafetyCampaignDetail(id)
      .then((res) => {
        setCampaign(res);
        if (res.results.length > 0) {
          // Select first failing result or first result
          const firstFail = res.results.find((r) => r.status === "fail") || res.results[0];
          setSelectedResult(firstFail);
        }
      })
      .catch((err) => setError(err.message || "Failed to load campaign details."))
      .finally(() => setLoading(false));
  }, [id]);

  const filteredResults = (campaign?.results || []).filter((r) => {
    if (categoryFilter !== "all" && r.category !== categoryFilter) return false;
    if (severityFilter !== "all" && r.severity !== severityFilter) return false;
    if (statusFilter !== "all" && r.status !== statusFilter) return false;
    if (search.trim()) {
      const q = search.toLowerCase();
      const matchId = r.stable_case_id.toLowerCase().includes(q);
      const matchInput = JSON.stringify(r.adversarial_input).toLowerCase().includes(q);
      const matchOutput = JSON.stringify(r.agent_output).toLowerCase().includes(q);
      if (!matchId && !matchInput && !matchOutput) return false;
    }
    return true;
  });

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 antialiased overflow-hidden">
      <Sidebar />
      <div className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <Navbar />

        <main className="p-6 lg:p-8 max-w-7xl w-full mx-auto space-y-6">
          {/* Breadcrumbs */}
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <Link href="/safety" className="hover:text-slate-200 transition">
              Safety
            </Link>
            <span>/</span>
            <Link href="/safety/campaigns" className="hover:text-slate-200 transition">
              Campaigns
            </Link>
            <span>/</span>
            <span className="text-slate-200 font-mono">{id.slice(0, 8)}...</span>
          </div>

          {/* Header */}
          {campaign && (
            <div className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 shadow-sm space-y-4">
              <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4">
                <div>
                  <div className="flex items-center space-x-2">
                    <span
                      className={`px-2.5 py-0.5 rounded-full text-xs font-semibold uppercase tracking-wider ${
                        campaign.status === "completed"
                          ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                          : campaign.status === "error"
                          ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                          : "bg-sky-500/10 text-sky-400 border border-sky-500/30"
                      }`}
                    >
                      {campaign.status}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">
                      Dataset: {campaign.dataset_name || "Benchmark"}
                    </span>
                  </div>

                  <h1 className="text-2xl font-bold text-white mt-1.5">{campaign.name}</h1>
                  {campaign.description && (
                    <p className="text-sm text-slate-400 mt-0.5">{campaign.description}</p>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <Link
                    href={`/safety/compare?b=${campaign.id}`}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-medium rounded-lg border border-slate-700 transition flex items-center space-x-2"
                  >
                    <svg className="w-3.5 h-3.5 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
                    </svg>
                    <span>Compare Against Baseline</span>
                  </Link>
                </div>
              </div>

              {/* Summary Stats Row */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-4 border-t border-slate-800">
                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Target Agent
                  </span>
                  <div className="text-sm font-medium text-slate-200 mt-0.5 font-mono">
                    {campaign.agent_name} <span className="text-xs text-slate-400">({campaign.agent_version})</span>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Safety Pass Rate
                  </span>
                  <div className="flex items-baseline space-x-1.5 mt-0.5">
                    <span className="text-lg font-bold text-white">
                      {campaign.safety_pass_rate !== null && campaign.safety_pass_rate !== undefined
                        ? `${(campaign.safety_pass_rate * 100).toFixed(1)}%`
                        : "—"}
                    </span>
                    <span className="text-xs text-slate-400">
                      ({campaign.passed_tests}/{campaign.total_tests})
                    </span>
                  </div>
                </div>

                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Critical Breaches
                  </span>
                  <div className="mt-0.5">
                    {campaign.critical_failures > 0 ? (
                      <span className="px-2 py-0.5 rounded text-xs font-bold bg-rose-500/10 text-rose-400 border border-rose-500/30">
                        {campaign.critical_failures} Critical Breaches
                      </span>
                    ) : (
                      <span className="px-2 py-0.5 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                        0 Breaches
                      </span>
                    )}
                  </div>
                </div>

                <div>
                  <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                    Execution Time
                  </span>
                  <span className="text-xs text-slate-300 font-mono mt-1 block">
                    {new Date(campaign.created_at).toLocaleString()}
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* Loading or Error */}
          {loading && (
            <div className="p-12 text-center text-slate-400">
              <div className="inline-block animate-spin h-6 w-6 border-2 border-emerald-400 border-t-transparent rounded-full mr-2" />
              Loading campaign execution results...
            </div>
          )}

          {error && (
            <div className="p-4 bg-rose-500/10 border border-rose-500/30 rounded-xl text-rose-400 text-sm">
              {error}
            </div>
          )}

          {/* Filter Bar */}
          {campaign && (
            <div className="flex flex-wrap items-center justify-between gap-3 bg-slate-900/60 p-4 rounded-xl border border-slate-800">
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={statusFilter}
                  onChange={(e) => setStatusFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                >
                  <option value="all">All Outcomes</option>
                  <option value="pass">Passed Only</option>
                  <option value="fail">Failed Only</option>
                  <option value="error">Errors</option>
                </select>

                <select
                  value={severityFilter}
                  onChange={(e) => setSeverityFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                >
                  <option value="all">All Severities</option>
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>

                <select
                  value={categoryFilter}
                  onChange={(e) => setCategoryFilter(e.target.value)}
                  className="bg-slate-950 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-300 focus:outline-none focus:border-emerald-500"
                >
                  <option value="all">All Threat Categories</option>
                  <option value="prompt_injection">Prompt Injection</option>
                  <option value="instruction_hierarchy">Instruction Hierarchy</option>
                  <option value="sensitive_data">Sensitive Data</option>
                  <option value="unsafe_tool_use">Unsafe Tool Use</option>
                  <option value="policy_boundary">Policy Boundary</option>
                  <option value="data_exfiltration">Data Exfiltration</option>
                  <option value="jailbreak_refusal">Jailbreak & Refusal</option>
                </select>
              </div>

              <div className="w-full sm:w-64">
                <input
                  type="text"
                  placeholder="Filter cases by keyword..."
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500/50"
                />
              </div>
            </div>
          )}

          {/* Master Detail View */}
          {campaign && (
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
              {/* Left Column: Test Case Results Table */}
              <div className="lg:col-span-7 bg-slate-900/60 border border-slate-800 rounded-xl overflow-hidden shadow-sm">
                <div className="p-4 border-b border-slate-800 flex items-center justify-between">
                  <h3 className="text-sm font-semibold text-white">
                    Adversarial Test Outcomes ({filteredResults.length} / {campaign.results.length})
                  </h3>
                  <span className="text-[11px] text-slate-400">Click a case to inspect evidence</span>
                </div>

                <div className="overflow-x-auto max-h-[600px] overflow-y-auto">
                  <table className="w-full text-left text-xs text-slate-300">
                    <thead className="bg-slate-950/80 uppercase text-[10px] text-slate-400 border-b border-slate-800 sticky top-0 z-10">
                      <tr>
                        <th className="px-4 py-2.5">Case ID</th>
                        <th className="px-4 py-2.5">Category</th>
                        <th className="px-4 py-2.5">Severity</th>
                        <th className="px-4 py-2.5">Outcome</th>
                        <th className="px-4 py-2.5">Duration</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {filteredResults.length === 0 && (
                        <tr>
                          <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                            No test cases match filter criteria.
                          </td>
                        </tr>
                      )}
                      {filteredResults.map((r) => {
                        const isSelected = selectedResult?.id === r.id;
                        return (
                          <tr
                            key={r.id}
                            onClick={() => setSelectedResult(r)}
                            className={`cursor-pointer transition ${
                              isSelected
                                ? "bg-emerald-500/10 border-l-2 border-emerald-400"
                                : "hover:bg-slate-800/40"
                            }`}
                          >
                            <td className="px-4 py-3 font-mono font-medium text-white">
                              {r.stable_case_id}
                            </td>
                            <td className="px-4 py-3 text-slate-300 capitalize">
                              {r.category.replace(/_/g, " ")}
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                  r.severity === "critical"
                                    ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                                    : r.severity === "high"
                                    ? "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                                    : "bg-slate-800 text-slate-400 border border-slate-700"
                                }`}
                              >
                                {r.severity}
                              </span>
                            </td>
                            <td className="px-4 py-3">
                              <span
                                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold flex items-center space-x-1 w-max ${
                                  r.status === "pass"
                                    ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                                    : r.status === "fail"
                                    ? "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                                    : "bg-amber-500/10 text-amber-400 border border-amber-500/30"
                                }`}
                              >
                                <span>{r.status === "pass" ? "PASSED" : r.status === "fail" ? "FAILED" : "ERROR"}</span>
                              </span>
                            </td>
                            <td className="px-4 py-3 font-mono text-slate-400">
                              {r.duration_ms ? `${r.duration_ms}ms` : "—"}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Right Column: Evidence & Evaluator Inspector Drawer */}
              <div className="lg:col-span-5 bg-slate-900/60 border border-slate-800 rounded-xl p-5 shadow-sm space-y-4 sticky top-6">
                {selectedResult ? (
                  <>
                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                      <div>
                        <span className="text-[10px] font-mono text-slate-400 uppercase tracking-wider block">
                          Inspection Drawer
                        </span>
                        <h4 className="text-base font-bold text-white font-mono mt-0.5">
                          {selectedResult.stable_case_id}
                        </h4>
                      </div>

                      <div className="flex items-center space-x-2">
                        <span
                          className={`px-2 py-0.5 rounded text-xs font-semibold ${
                            selectedResult.status === "pass"
                              ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/30"
                              : "bg-rose-500/10 text-rose-400 border border-rose-500/30"
                          }`}
                        >
                          {selectedResult.status.toUpperCase()}
                        </span>

                        {selectedResult.run_id && (
                          <Link
                            href={`/runs/${selectedResult.run_id}`}
                            className="text-xs px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded border border-slate-700 transition flex items-center space-x-1"
                            title="View trace waterfall in Runs Explorer"
                          >
                            <span>Trace Waterfall</span>
                            <svg className="w-3 h-3 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                            </svg>
                          </Link>
                        )}
                      </div>
                    </div>

                    {/* Adversarial Attack Input */}
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                        Adversarial Attack Input
                      </span>
                      <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 overflow-x-auto whitespace-pre-wrap font-mono">
                        {typeof selectedResult.adversarial_input === "object"
                          ? JSON.stringify(selectedResult.adversarial_input, null, 2)
                          : String(selectedResult.adversarial_input)}
                      </pre>
                    </div>

                    {/* Expected Safe Behavior */}
                    {selectedResult.expected_safe_behavior && (
                      <div className="space-y-1.5">
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                          Expected Safe Behavior
                        </span>
                        <div className="p-3 bg-slate-950/70 border border-slate-800 rounded-lg text-xs text-slate-300">
                          {selectedResult.expected_safe_behavior}
                        </div>
                      </div>
                    )}

                    {/* Actual Agent Response */}
                    <div className="space-y-1.5">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                        Actual Agent Response
                      </span>
                      <pre className="p-3 bg-slate-950 border border-slate-800 rounded-lg text-xs text-slate-200 overflow-x-auto whitespace-pre-wrap font-mono max-h-40">
                        {typeof selectedResult.agent_output === "object"
                          ? JSON.stringify(selectedResult.agent_output, null, 2)
                          : String(selectedResult.agent_output || "No output recorded")}
                      </pre>
                    </div>

                    {/* Redacted Sensitive Evidence Drawer */}
                    {selectedResult.evidence && (
                      <div className="space-y-1.5">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] font-semibold text-rose-400 uppercase tracking-wider flex items-center space-x-1">
                            <svg className="w-3.5 h-3.5 text-rose-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                            </svg>
                            <span>Redacted Evidence & Breaches</span>
                          </span>
                          <span className="text-[10px] text-slate-500 font-mono">Sanitized View</span>
                        </div>
                        <pre className="p-3 bg-rose-950/20 border border-rose-900/40 rounded-lg text-xs text-rose-300 overflow-x-auto whitespace-pre-wrap font-mono">
                          {typeof selectedResult.evidence === "object"
                            ? JSON.stringify(selectedResult.evidence, null, 2)
                            : String(selectedResult.evidence)}
                        </pre>
                      </div>
                    )}

                    {/* Evaluator Explanations */}
                    <div className="space-y-2 pt-2 border-t border-slate-800">
                      <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block">
                        Evaluators Executed ({selectedResult.evaluator_results.length})
                      </span>
                      <div className="space-y-2 max-h-56 overflow-y-auto">
                        {selectedResult.evaluator_results.map((ev, i) => (
                          <div
                            key={i}
                            className="p-2.5 bg-slate-950 border border-slate-800/80 rounded-lg text-xs space-y-1"
                          >
                            <div className="flex items-center justify-between font-medium">
                              <span className="text-slate-200 font-mono">{ev.evaluator_name}</span>
                              <span
                                className={`px-1.5 py-0.5 rounded text-[10px] font-semibold uppercase ${
                                  ev.passed
                                    ? "bg-emerald-500/10 text-emerald-400"
                                    : "bg-rose-500/10 text-rose-400"
                                }`}
                              >
                                {ev.passed ? "Passed" : "Failed"} (Score: {ev.score})
                              </span>
                            </div>
                            <p className="text-slate-400 text-[11px]">{ev.explanation}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  </>
                ) : (
                  <div className="p-12 text-center text-slate-500 text-xs">
                    Select a test case from the table to inspect details.
                  </div>
                )}
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
