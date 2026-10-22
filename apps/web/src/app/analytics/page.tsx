"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import {
  fetchAnalyticsAgents,
  fetchAnalyticsModels,
  fetchAnalyticsOverview,
  fetchAnalyticsTimeseries,
  fetchCostBreakdown,
} from "@/lib/api";
import {
  AgentUsageItem,
  AgentsAnalytics,
  AnalyticsOverview,
  AnalyticsTimeseries,
  CostBreakdown,
  ModelUsageItem,
  ModelsAnalytics,
  TimeseriesPoint,
} from "@/lib/types";

export default function AnalyticsPage() {
  const [timeRange, setTimeRange] = useState<string>("7d");
  const [agentFilter, setAgentFilter] = useState<string>("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Data states
  const [overview, setOverview] = useState<AnalyticsOverview | null>(null);
  const [timeseries, setTimeseries] = useState<AnalyticsTimeseries | null>(null);
  const [models, setModels] = useState<ModelsAnalytics | null>(null);
  const [agents, setAgents] = useState<AgentsAnalytics | null>(null);
  const [costBreakdown, setCostBreakdown] = useState<CostBreakdown | null>(null);

  // Active hover tooltip state for charts
  const [hoveredPoint, setHoveredPoint] = useState<TimeseriesPoint | null>(null);

  const loadAllAnalytics = async (range = timeRange, agent = agentFilter) => {
    setLoading(true);
    setError(null);
    try {
      const agentParam = agent === "all" ? undefined : agent;
      const [ovRes, tsRes, modRes, agRes, costRes] = await Promise.all([
        fetchAnalyticsOverview({ timeRange: range, agentName: agentParam }),
        fetchAnalyticsTimeseries({ timeRange: range, agentName: agentParam }),
        fetchAnalyticsModels({ timeRange: range }),
        fetchAnalyticsAgents({ timeRange: range }),
        fetchCostBreakdown({ timeRange: range }),
      ]);
      setOverview(ovRes);
      setTimeseries(tsRes);
      setModels(modRes);
      setAgents(agRes);
      setCostBreakdown(costRes);
    } catch (err: any) {
      setError(err.message || "Failed to load analytics data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadAllAnalytics(timeRange, agentFilter);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [timeRange, agentFilter]);

  const points = timeseries?.points || [];

  // Helper formatting
  const formatCost = (val: number | null | undefined) => {
    if (val === null || val === undefined) return "$0.00";
    return `$${val.toFixed(val < 0.01 && val > 0 ? 4 : 2)}`;
  };

  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return "0";
    return num.toLocaleString();
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title="Advanced Analytics" />

        <main className="p-8 space-y-8 flex-1 overflow-y-auto max-w-7xl w-full mx-auto">
          {/* Header & Controls */}
          <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">Advanced Analytics & Observability</h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  Phase 4
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Aggregated agent telemetry, latency percentiles, model attribution, and token economics.
              </p>
            </div>

            {/* Filter controls */}
            <div className="flex flex-wrap items-center gap-3">
              {/* Agent Filter */}
              <div className="flex items-center space-x-1.5 bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-xs">
                <span className="text-slate-400">Agent:</span>
                <select
                  value={agentFilter}
                  onChange={(e) => setAgentFilter(e.target.value)}
                  className="bg-transparent text-slate-200 focus:outline-none cursor-pointer"
                  disabled={loading}
                >
                  <option value="all" className="bg-slate-900 text-slate-200">All Agents</option>
                  {agents?.items?.map((a: AgentUsageItem) => (
                    <option key={`${a.agent_name}-${a.agent_version}`} value={a.agent_name} className="bg-slate-900 text-slate-200">
                      {a.agent_name} (v{a.agent_version})
                    </option>
                  ))}
                </select>
              </div>

              {/* Time Range Selector */}
              <div className="inline-flex rounded-lg bg-slate-900 border border-slate-800 p-0.5 text-xs">
                {[
                  { id: "24h", label: "24h" },
                  { id: "7d", label: "7d" },
                  { id: "30d", label: "30d" },
                  { id: "all", label: "All" },
                ].map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setTimeRange(item.id)}
                    className={`px-3 py-1 rounded-md font-medium transition ${
                      timeRange === item.id
                        ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                        : "text-slate-400 hover:text-slate-200"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>

              {/* Refresh Button */}
              <button
                onClick={() => loadAllAnalytics(timeRange, agentFilter)}
                disabled={loading}
                className="px-3 py-1.5 text-xs rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-300 transition border border-slate-800 flex items-center space-x-1.5 disabled:opacity-50"
                title="Reload latest metrics"
              >
                <svg
                  className={`w-3.5 h-3.5 ${loading ? "animate-spin text-emerald-400" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                  />
                </svg>
                <span>Refresh</span>
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
              <span>{error}</span>
              <button
                onClick={() => loadAllAnalytics(timeRange, agentFilter)}
                className="underline hover:text-rose-100 font-medium"
              >
                Try Again
              </button>
            </div>
          )}

          {/* KPI Cards Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4">
            {/* 1. Total Runs */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm relative overflow-hidden">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Total Executions</div>
              <div className="text-2xl font-bold text-white mt-1">
                {loading && !overview ? "..." : formatNumber(overview?.total_runs)}
              </div>
              <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-2">
                <span className="text-emerald-400 font-medium">{overview?.successful_runs ?? 0} ok</span>
                <span>•</span>
                <span className="text-rose-400 font-medium">{overview?.failed_runs ?? 0} err</span>
              </div>
            </div>

            {/* 2. Success & Error Rate */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm relative overflow-hidden">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Success / Error Rate</div>
              <div className="flex items-baseline space-x-2 mt-1">
                <span className="text-2xl font-bold text-emerald-400">
                  {overview ? `${((1 - (overview.error_rate || 0)) * 100).toFixed(1)}%` : "..."}
                </span>
                <span className="text-xs text-rose-400 font-medium">
                  {overview ? `(${((overview.error_rate || 0) * 100).toFixed(1)}% err)` : ""}
                </span>
              </div>
              <div className="w-full bg-slate-800 rounded-full h-1.5 mt-3 overflow-hidden">
                <div
                  className="bg-emerald-400 h-1.5 transition-all duration-500"
                  style={{ width: `${overview ? (1 - (overview.error_rate || 0)) * 100 : 0}%` }}
                />
              </div>
            </div>

            {/* 3. Latency Percentiles */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm relative overflow-hidden">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Latency (p50 / p95)</div>
              <div className="text-2xl font-bold text-white mt-1">
                {overview?.p50_duration_ms ? `${Math.round(overview.p50_duration_ms)}ms` : "0ms"}
              </div>
              <div className="text-[11px] text-slate-400 mt-2">
                <span className="text-amber-400 font-medium">p95: {overview?.p95_duration_ms ? `${Math.round(overview.p95_duration_ms)}ms` : "0ms"}</span>
                <span className="text-slate-500 ml-1">avg: {overview?.avg_duration_ms ? `${Math.round(overview.avg_duration_ms)}ms` : "0ms"}</span>
              </div>
            </div>

            {/* 4. Token Burn */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm relative overflow-hidden">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Token Volume</div>
              <div className="text-2xl font-bold text-white mt-1">
                {loading && !overview ? "..." : formatNumber(overview?.total_tokens)}
              </div>
              <div className="text-[11px] text-slate-400 mt-2">
                <span>Total Recorded Tokens</span>
              </div>
            </div>

            {/* 5. Estimated Cost */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm relative overflow-hidden">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Estimated Model Cost</div>
              <div className="text-2xl font-bold text-white mt-1">
                {loading && !overview ? "..." : formatCost(overview?.total_cost_usd)}
              </div>
              <div className="text-[11px] text-slate-400 mt-2 flex items-center justify-between">
                <span>{overview?.cost_reported_runs ?? 0} metered</span>
                {overview && (overview.unmetered_runs ?? 0) > 0 && (
                  <span className="text-amber-400" title="Runs without recorded cost">
                    {overview.unmetered_runs} unmetered
                  </span>
                )}
              </div>
            </div>

            {/* 6. Evaluation Pass Rate */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm relative overflow-hidden">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Eval Pass Rate</div>
              <div className="text-2xl font-bold text-white mt-1">
                {overview?.eval_pass_rate !== null && overview?.eval_pass_rate !== undefined
                  ? `${(overview.eval_pass_rate * 100).toFixed(1)}%`
                  : "N/A"}
              </div>
              <div className="text-[11px] text-slate-400 mt-2">
                <span className="text-slate-400">
                  {overview?.regression_count !== undefined ? `${overview.regression_count} regressions` : "0 regressions"}
                </span>
              </div>
            </div>
          </div>

          {/* Time Series Charts Section */}
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Execution & Latency Trends</h2>
                <p className="text-xs text-slate-400">Continuous telemetry bucketed by {timeseries?.interval || "hour"}</p>
              </div>
              {hoveredPoint && (
                <div className="text-xs bg-slate-900 border border-slate-800 px-3 py-1 rounded-md text-slate-300">
                  <span className="text-slate-500 mr-2">{hoveredPoint.timestamp}</span>
                  <span className="font-medium text-white">{hoveredPoint.total_runs} runs</span>
                  <span className="text-rose-400 ml-2">{(hoveredPoint.error_rate * 100).toFixed(1)}% err</span>
                  <span className="text-amber-400 ml-2">p95: {Math.round(hoveredPoint.p95_duration_ms)}ms</span>
                </div>
              )}
            </div>

            {/* Visual SVG Chart: Volume & Error Trend */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <span className="text-xs font-medium uppercase tracking-wider text-slate-400">Run Volume & Error Rate (%)</span>
                <div className="flex items-center space-x-4 text-xs">
                  <div className="flex items-center space-x-1.5">
                    <span className="w-3 h-3 rounded-sm bg-emerald-500/80 inline-block" />
                    <span className="text-slate-400">Runs</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <span className="w-3 h-0.5 bg-rose-400 inline-block" />
                    <span className="text-slate-400">Error Rate</span>
                  </div>
                </div>
              </div>

              {points.length === 0 ? (
                <div className="h-48 flex items-center justify-center text-slate-500 text-xs">
                  No telemetry recorded for this time window.
                </div>
              ) : (
                <div className="relative h-56 w-full">
                  {/* SVG Chart */}
                  <svg
                    viewBox={`0 0 ${Math.max(points.length * 30, 600)} 180`}
                    preserveAspectRatio="none"
                    className="w-full h-full overflow-visible"
                  >
                    <defs>
                      <linearGradient id="barGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity="0.8" />
                        <stop offset="100%" stopColor="#10b981" stopOpacity="0.2" />
                      </linearGradient>
                    </defs>

                    {/* Horizontal grid lines */}
                    {[0, 45, 90, 135].map((y) => (
                      <line
                        key={y}
                        x1="0"
                        y1={y}
                        x2={Math.max(points.length * 30, 600)}
                        y2={y}
                        stroke="#1e293b"
                        strokeDasharray="4 4"
                      />
                    ))}

                    {/* Bars for Run Volume */}
                    {(() => {
                      const maxRuns = Math.max(...points.map((p) => p.total_runs), 5);
                      const width = Math.max(points.length * 30, 600);
                      const barWidth = Math.max(width / points.length - 8, 4);

                      return points.map((p, i) => {
                        const x = (i / points.length) * width + 4;
                        const height = (p.total_runs / maxRuns) * 140;
                        const y = 160 - height;
                        return (
                          <g
                            key={p.timestamp}
                            onMouseEnter={() => setHoveredPoint(p)}
                            onMouseLeave={() => setHoveredPoint(null)}
                            className="cursor-pointer group"
                          >
                            <rect
                              x={x}
                              y={y}
                              width={barWidth}
                              height={Math.max(height, 2)}
                              rx="3"
                              fill="url(#barGrad)"
                              className="group-hover:opacity-100 transition-opacity"
                            />
                            {/* Error overlay on bar */}
                            {p.failed_runs > 0 && (
                              <rect
                                x={x}
                                y={160 - (p.failed_runs / maxRuns) * 140}
                                width={barWidth}
                                height={Math.max((p.failed_runs / maxRuns) * 140, 2)}
                                rx="3"
                                fill="#f43f5e"
                                opacity="0.9"
                              />
                            )}
                          </g>
                        );
                      });
                    })()}

                    {/* Error rate line */}
                    {(() => {
                      const width = Math.max(points.length * 30, 600);
                      const coords = points.map((p, i) => {
                        const x = (i / points.length) * width + (width / points.length) / 2;
                        const y = 160 - p.error_rate * 140;
                        return `${x},${y}`;
                      });
                      return (
                        <polyline
                          fill="none"
                          stroke="#f43f5e"
                          strokeWidth="2"
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          points={coords.join(" ")}
                        />
                      );
                    })()}
                  </svg>

                  {/* X-axis labels preview */}
                  <div className="flex justify-between text-[10px] text-slate-500 mt-2 px-1">
                    <span>{points[0]?.timestamp.split("T")[0]}</span>
                    <span>{points[Math.floor(points.length / 2)]?.timestamp.split("T")[0]}</span>
                    <span>{points[points.length - 1]?.timestamp.split("T")[0]}</span>
                  </div>
                </div>
              )}
            </div>

            {/* Latency & Token Trends Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Latency Percentiles Chart */}
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-medium uppercase tracking-wider text-slate-400">Latency Percentiles (ms)</span>
                  <div className="flex items-center space-x-3 text-xs">
                    <span className="text-emerald-400 font-medium">● p50</span>
                    <span className="text-amber-400 font-medium">● p95</span>
                  </div>
                </div>

                {points.length === 0 ? (
                  <div className="h-40 flex items-center justify-center text-slate-500 text-xs">
                    No latency telemetry.
                  </div>
                ) : (
                  <div className="h-44 w-full">
                    <svg viewBox={`0 0 ${Math.max(points.length * 20, 400)} 140`} preserveAspectRatio="none" className="w-full h-full">
                      {/* Grid */}
                      {[0, 35, 70, 105].map((y) => (
                        <line key={y} x1="0" y1={y} x2={Math.max(points.length * 20, 400)} y2={y} stroke="#1e293b" strokeDasharray="3 3" />
                      ))}
                      {/* p95 line */}
                      {(() => {
                        const maxLat = Math.max(...points.map((p) => p.p95_duration_ms), 100);
                        const width = Math.max(points.length * 20, 400);
                        const p95Coords = points.map((p, i) => {
                          const x = (i / Math.max(points.length - 1, 1)) * width;
                          const y = 120 - (p.p95_duration_ms / maxLat) * 110;
                          return `${x},${y}`;
                        });
                        const p50Coords = points.map((p, i) => {
                          const x = (i / Math.max(points.length - 1, 1)) * width;
                          const y = 120 - (p.p50_duration_ms / maxLat) * 110;
                          return `${x},${y}`;
                        });
                        return (
                          <>
                            <polyline fill="none" stroke="#fbbf24" strokeWidth="2" strokeDasharray="2 2" points={p95Coords.join(" ")} />
                            <polyline fill="none" stroke="#10b981" strokeWidth="2" points={p50Coords.join(" ")} />
                          </>
                        );
                      })()}
                    </svg>
                  </div>
                )}
              </div>

              {/* Token & Cost Trend */}
              <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 shadow-sm">
                <div className="flex items-center justify-between mb-4">
                  <span className="text-xs font-medium uppercase tracking-wider text-slate-400">Tokens & Cost Trends</span>
                  <div className="flex items-center space-x-3 text-xs">
                    <span className="text-cyan-400 font-medium">● Tokens</span>
                    <span className="text-purple-400 font-medium">● Cost ($)</span>
                  </div>
                </div>

                {points.length === 0 ? (
                  <div className="h-40 flex items-center justify-center text-slate-500 text-xs">
                    No token or cost telemetry.
                  </div>
                ) : (
                  <div className="h-44 w-full">
                    <svg viewBox={`0 0 ${Math.max(points.length * 20, 400)} 140`} preserveAspectRatio="none" className="w-full h-full">
                      {[0, 35, 70, 105].map((y) => (
                        <line key={y} x1="0" y1={y} x2={Math.max(points.length * 20, 400)} y2={y} stroke="#1e293b" strokeDasharray="3 3" />
                      ))}
                      {(() => {
                        const maxTokens = Math.max(...points.map((p) => p.total_tokens), 100);
                        const width = Math.max(points.length * 20, 400);
                        const tokenCoords = points.map((p, i) => {
                          const x = (i / Math.max(points.length - 1, 1)) * width;
                          const y = 120 - (p.total_tokens / maxTokens) * 110;
                          return `${x},${y}`;
                        });
                        return (
                          <polyline fill="none" stroke="#38bdf8" strokeWidth="2" points={tokenCoords.join(" ")} />
                        );
                      })()}
                    </svg>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Model Breakdown & Agent Comparison Tables */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Model Breakdown */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-white">Model Usage & Economics</h3>
                  <p className="text-xs text-slate-400">Aggregated LLM calls, token burn, and costs by model</p>
                </div>
              </div>

              {!models || models.items.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  No LLM model spans recorded in this window.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="pb-2 font-medium">Model</th>
                        <th className="pb-2 font-medium text-right">Calls</th>
                        <th className="pb-2 font-medium text-right">Tokens</th>
                        <th className="pb-2 font-medium text-right">Est. Cost</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {models.items.map((m: ModelUsageItem) => (
                        <tr key={m.model} className="hover:bg-slate-800/30">
                          <td className="py-2.5 font-medium text-slate-200">{m.model}</td>
                          <td className="py-2.5 text-right text-slate-300">{formatNumber(m.call_count)}</td>
                          <td className="py-2.5 text-right text-slate-300">{formatNumber(m.total_tokens)}</td>
                          <td className="py-2.5 text-right text-emerald-400 font-medium">
                            {formatCost(m.total_cost_usd)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Agent Comparison */}
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-6 shadow-sm">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h3 className="text-sm font-semibold text-white">Agent Comparison</h3>
                  <p className="text-xs text-slate-400">Performance and reliability across deployed agents</p>
                </div>
              </div>

              {!agents || agents.items.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  No agent execution data recorded in this window.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="pb-2 font-medium">Agent</th>
                        <th className="pb-2 font-medium text-right">Runs</th>
                        <th className="pb-2 font-medium text-right">Success</th>
                        <th className="pb-2 font-medium text-right">p95 Latency</th>
                        <th className="pb-2 font-medium text-right">Est. Cost</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {agents.items.map((a: AgentUsageItem) => (
                        <tr key={`${a.agent_name}-${a.agent_version}`} className="hover:bg-slate-800/30">
                          <td className="py-2.5">
                            <span className="font-medium text-slate-200 block">{a.agent_name}</span>
                            <span className="text-[10px] text-slate-500">v{a.agent_version}</span>
                          </td>
                          <td className="py-2.5 text-right text-slate-300">{formatNumber(a.total_runs)}</td>
                          <td className="py-2.5 text-right">
                            <span className={a.error_rate > 0.05 ? "text-amber-400" : "text-emerald-400"}>
                              {((1 - a.error_rate) * 100).toFixed(1)}%
                            </span>
                          </td>
                          <td className="py-2.5 text-right text-slate-300">
                            {a.p95_duration_ms ? `${Math.round(a.p95_duration_ms)}ms` : "0ms"}
                          </td>
                          <td className="py-2.5 text-right text-emerald-400 font-medium">
                            {formatCost(a.total_cost_usd)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Quick Links / Navigation Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-800/80 text-xs text-slate-500">
            <span>TraceHarbor Phase 4 Analytics Engine</span>
            <div className="flex items-center space-x-4">
              <Link href="/runs" className="text-slate-400 hover:text-white transition">
                Runs Explorer →
              </Link>
              <Link href="/alerts" className="text-slate-400 hover:text-white transition">
                Alerts & Monitoring →
              </Link>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
