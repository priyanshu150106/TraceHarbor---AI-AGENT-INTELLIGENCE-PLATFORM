"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import {
  createAlertRule,
  deleteAlertRule,
  evaluateAlertRules,
  fetchAlertHistory,
  fetchAlertRules,
  testAlertRule,
  updateAlertRule,
} from "@/lib/api";
import {
  AlertEvaluationBatch,
  AlertEvaluationResult,
  AlertHistory,
  AlertRule,
  AlertRuleCreate,
} from "@/lib/types";

export default function AlertsPage() {
  const [rules, setRules] = useState<AlertRule[]>([]);
  const [history, setHistory] = useState<AlertHistory[]>([]);
  const [totalHistory, setTotalHistory] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [showModal, setShowModal] = useState(false);
  const [editingRule, setEditingRule] = useState<AlertRule | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  // Form inputs
  const [ruleName, setRuleName] = useState("");
  const [ruleMetric, setRuleMetric] = useState("error_rate");
  const [ruleOperator, setRuleOperator] = useState(">");
  const [ruleThreshold, setRuleThreshold] = useState("0.05");
  const [ruleWindowMinutes, setRuleWindowMinutes] = useState("60");
  const [ruleCooldown, setRuleCooldown] = useState("30");
  const [ruleChannel, setRuleChannel] = useState("in_app");
  const [ruleWebhookUrl, setRuleWebhookUrl] = useState("");
  const [ruleWebhookSecret, setRuleWebhookSecret] = useState("");

  // Testing & Evaluation state
  const [evaluating, setEvaluating] = useState(false);
  const [evalResult, setEvalResult] = useState<AlertEvaluationBatch | null>(null);
  const [testingRuleId, setTestingRuleId] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<AlertEvaluationResult | null>(null);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [rulesRes, histRes] = await Promise.all([
        fetchAlertRules(),
        fetchAlertHistory({ limit: 50 }),
      ]);
      setRules(rulesRes);
      setHistory(histRes.items);
      setTotalHistory(histRes.total);
    } catch (err: any) {
      setError(err.message || "Failed to load alerts data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const openCreateModal = () => {
    setEditingRule(null);
    setRuleName("");
    setRuleMetric("error_rate");
    setRuleOperator(">");
    setRuleThreshold("0.05");
    setRuleWindowMinutes("60");
    setRuleCooldown("30");
    setRuleChannel("in_app");
    setRuleWebhookUrl("");
    setRuleWebhookSecret("");
    setFormError(null);
    setShowModal(true);
  };

  const openEditModal = (rule: AlertRule) => {
    setEditingRule(rule);
    setRuleName(rule.name);
    setRuleMetric(rule.metric);
    setRuleOperator(rule.operator);
    setRuleThreshold(rule.threshold.toString());
    setRuleWindowMinutes(rule.window_minutes.toString());
    setRuleCooldown(rule.cooldown_minutes.toString());
    setRuleChannel(rule.channel);
    setRuleWebhookUrl(rule.webhook_url || "");
    setRuleWebhookSecret("");
    setFormError(null);
    setShowModal(true);
  };

  const handleSaveRule = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!ruleName.trim()) {
      setFormError("Rule name is required.");
      return;
    }

    const parsedThreshold = parseFloat(ruleThreshold);
    if (isNaN(parsedThreshold)) {
      setFormError("Threshold must be a valid number.");
      return;
    }

    const parsedWindow = parseInt(ruleWindowMinutes, 10);
    if (isNaN(parsedWindow) || parsedWindow < 1) {
      setFormError("Window minutes must be at least 1.");
      return;
    }

    const parsedCooldown = parseInt(ruleCooldown, 10);
    if (isNaN(parsedCooldown) || parsedCooldown < 1) {
      setFormError("Cooldown must be at least 1 minute.");
      return;
    }

    setSubmitting(true);
    setFormError(null);

    try {
      if (editingRule) {
        await updateAlertRule(editingRule.id, {
          name: ruleName.trim(),
          metric: ruleMetric,
          operator: ruleOperator,
          threshold: parsedThreshold,
          window_minutes: parsedWindow,
          cooldown_minutes: parsedCooldown,
          channel: ruleChannel,
          webhook_url: ruleWebhookUrl.trim() || undefined,
          webhook_secret: ruleWebhookSecret.trim() || undefined,
        });
      } else {
        const payload: AlertRuleCreate = {
          name: ruleName.trim(),
          metric: ruleMetric,
          operator: ruleOperator,
          threshold: parsedThreshold,
          window_minutes: parsedWindow,
          cooldown_minutes: parsedCooldown,
          channel: ruleChannel,
          webhook_url: ruleWebhookUrl.trim() || undefined,
          webhook_secret: ruleWebhookSecret.trim() || undefined,
        };
        await createAlertRule(payload);
      }
      setShowModal(false);
      loadData();
    } catch (err: any) {
      setFormError(err.message || "Failed to save alert rule.");
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleActive = async (rule: AlertRule) => {
    try {
      await updateAlertRule(rule.id, { is_active: !rule.is_active });
      setRules((prev) =>
        prev.map((r) => (r.id === rule.id ? { ...r, is_active: !r.is_active } : r))
      );
    } catch (err: any) {
      setError(err.message || "Failed to toggle rule state.");
    }
  };

  const handleDeleteRule = async (ruleId: string) => {
    if (!confirm("Are you sure you want to delete this alert rule?")) return;
    try {
      await deleteAlertRule(ruleId);
      setRules((prev) => prev.filter((r) => r.id !== ruleId));
    } catch (err: any) {
      setError(err.message || "Failed to delete alert rule.");
    }
  };

  const handleEvaluateNow = async () => {
    setEvaluating(true);
    setEvalResult(null);
    setTestResult(null);
    try {
      const res = await evaluateAlertRules();
      setEvalResult(res);
      // Reload history to show any freshly triggered alerts
      const histRes = await fetchAlertHistory({ limit: 50 });
      setHistory(histRes.items);
      setTotalHistory(histRes.total);
    } catch (err: any) {
      setError(err.message || "Evaluation failed.");
    } finally {
      setEvaluating(false);
    }
  };

  const handleTestRule = async (ruleId: string) => {
    setTestingRuleId(ruleId);
    setTestResult(null);
    try {
      const res = await testAlertRule(ruleId);
      setTestResult(res);
    } catch (err: any) {
      setError(err.message || "Testing rule failed.");
    } finally {
      setTestingRuleId(null);
    }
  };

  const formatMetricLabel = (m: string) => {
    switch (m) {
      case "error_rate":
        return "Error Rate";
      case "p95_latency_ms":
        return "p95 Latency";
      case "total_cost":
        return "Estimated Cost";
      case "eval_pass_rate":
        return "Eval Pass Rate";
      case "regression_count":
        return "Regression Count";
      default:
        return m;
    }
  };

  const formatWindowLabel = (mins: number) => {
    if (mins >= 1440) {
      const days = Math.round(mins / 1440);
      return `${days}d (${mins}m)`;
    }
    if (mins >= 60) {
      const hrs = Math.round(mins / 60);
      return `${hrs}h (${mins}m)`;
    }
    return `${mins}m`;
  };

  const formatThresholdDisplay = (metric: string, op: string, th: number) => {
    if (metric === "error_rate" || metric === "eval_pass_rate") {
      return `${op} ${(th * 100).toFixed(1)}%`;
    }
    if (metric === "p95_latency_ms") {
      return `${op} ${Math.round(th)}ms`;
    }
    if (metric === "total_cost") {
      return `${op} $${th.toFixed(2)}`;
    }
    return `${op} ${th}`;
  };

  const formatObservedValue = (metric: string, val: number | null | undefined) => {
    if (val === null || val === undefined) return "N/A";
    if (metric === "error_rate" || metric === "eval_pass_rate") {
      return `${(val * 100).toFixed(1)}%`;
    }
    if (metric === "p95_latency_ms") {
      return `${Math.round(val)}ms`;
    }
    if (metric === "total_cost") {
      return `$${val.toFixed(4)}`;
    }
    return val.toString();
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title="Alerts & Monitoring" />

        <main className="p-8 space-y-8 flex-1 overflow-y-auto max-w-7xl w-full mx-auto">
          {/* Header & Global Actions */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <div className="flex items-center space-x-2">
                <h1 className="text-2xl font-bold tracking-tight text-white">Alert Rules & Monitoring</h1>
                <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  Phase 4
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Configure threshold alerts for error rates, latency spikes, budget limits, and evaluation regressions.
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={handleEvaluateNow}
                disabled={evaluating || loading}
                className="px-3.5 py-1.5 text-xs rounded-lg bg-slate-900 hover:bg-slate-800 text-slate-200 transition border border-slate-800 flex items-center space-x-1.5 disabled:opacity-50"
              >
                <svg
                  className={`w-3.5 h-3.5 ${evaluating ? "animate-spin text-emerald-400" : ""}`}
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M13 10V3L4 14h7v7l9-11h-7z"
                  />
                </svg>
                <span>{evaluating ? "Evaluating..." : "Evaluate Rules Now"}</span>
              </button>

              <button
                onClick={openCreateModal}
                className="px-3.5 py-1.5 text-xs rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition shadow-sm flex items-center space-x-1.5"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                <span>Create Alert Rule</span>
              </button>
            </div>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs flex items-center justify-between">
              <span>{error}</span>
              <button onClick={loadData} className="underline hover:text-rose-100 font-medium">
                Dismiss & Retry
              </button>
            </div>
          )}

          {/* Evaluation Batch Results Banner */}
          {evalResult && (
            <div className="p-4 rounded-xl bg-slate-900 border border-emerald-500/30 text-xs space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-400" />
                  <span className="font-semibold text-white">Evaluation Completed</span>
                  <span className="text-slate-400">
                    ({evalResult.rules_evaluated} rules evaluated, {evalResult.alerts_triggered} triggered)
                  </span>
                </div>
                <button
                  onClick={() => setEvalResult(null)}
                  className="text-slate-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2 pt-1">
                {evalResult.results.map((r) => (
                  <div
                    key={r.rule_id}
                    className={`p-2 rounded-lg border text-[11px] ${
                      r.triggered
                        ? r.cooldown_active
                          ? "bg-amber-500/10 border-amber-500/30 text-amber-300"
                          : "bg-rose-500/10 border-rose-500/30 text-rose-300"
                        : "bg-slate-950/40 border-slate-800 text-slate-400"
                    }`}
                  >
                    <div className="font-medium text-white">{r.rule_name}</div>
                    <div className="mt-0.5">
                      Observed: {formatObservedValue(r.metric, r.observed_value)} ({r.operator} {r.threshold})
                    </div>
                    <div className="text-[10px] text-slate-500 mt-1">
                      {r.triggered
                        ? r.cooldown_active
                          ? "Triggered (Cooldown Active)"
                          : "Triggered & Dispatched"
                        : "Within Normal Thresholds"}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Single Rule Test Result Banner */}
          {testResult && (
            <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 text-xs space-y-1">
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white">Rule Test: {testResult.rule_name}</span>
                <button onClick={() => setTestResult(null)} className="text-slate-400 hover:text-white">
                  ✕
                </button>
              </div>
              <p className="text-slate-300">
                Metric: <span className="text-white font-medium">{formatMetricLabel(testResult.metric)}</span> • Observed Value:{" "}
                <span className="text-amber-400 font-bold">
                  {formatObservedValue(testResult.metric, testResult.observed_value)}
                </span>{" "}
                (Threshold: {testResult.operator} {testResult.threshold})
              </p>
              <p className="text-slate-400 text-[11px]">
                Status:{" "}
                <span className={testResult.triggered ? "text-rose-400 font-medium" : "text-emerald-400 font-medium"}>
                  {testResult.triggered ? "TRIGGER CONDITION MET" : "NORMAL (Threshold Not Met)"}
                </span>
                {testResult.cooldown_active && " — Cooldown currently active"}
              </p>
            </div>
          )}

          {/* Quick Metrics Cards */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Configured Rules</div>
              <div className="text-2xl font-bold text-white mt-1">{rules.length}</div>
              <div className="text-[11px] text-slate-500 mt-1">
                {rules.filter((r) => r.is_active).length} active • {rules.filter((r) => !r.is_active).length} disabled
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Total Fired Events</div>
              <div className="text-2xl font-bold text-white mt-1">{totalHistory}</div>
              <div className="text-[11px] text-slate-500 mt-1">Recorded alert incidents</div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl p-4 shadow-sm">
              <div className="text-[11px] font-medium uppercase tracking-wider text-slate-400">Notification Channels</div>
              <div className="text-2xl font-bold text-white mt-1">In-App & Webhook</div>
              <div className="text-[11px] text-emerald-400 mt-1">SSRF-protected outbound HTTP</div>
            </div>
          </div>

          {/* Alert Rules Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Configured Rules</h2>
                <p className="text-xs text-slate-400">Active threshold monitors evaluating agent telemetry</p>
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden shadow-sm">
              {loading && rules.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-400">Loading alert rules...</div>
              ) : rules.length === 0 ? (
                <div className="p-12 text-center space-y-3">
                  <div className="h-10 w-10 mx-auto rounded-full bg-slate-800 flex items-center justify-center text-slate-400">
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"
                      />
                    </svg>
                  </div>
                  <p className="text-xs text-slate-400">No alert rules configured yet.</p>
                  <button
                    onClick={openCreateModal}
                    className="text-xs text-emerald-400 hover:text-emerald-300 font-medium"
                  >
                    + Create your first alert rule
                  </button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-950/40 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="py-3 px-4 font-medium">Rule Name</th>
                        <th className="py-3 px-4 font-medium">Metric</th>
                        <th className="py-3 px-4 font-medium">Threshold</th>
                        <th className="py-3 px-4 font-medium">Window</th>
                        <th className="py-3 px-4 font-medium">Channel</th>
                        <th className="py-3 px-4 font-medium">Status</th>
                        <th className="py-3 px-4 font-medium text-right">Actions</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {rules.map((rule) => (
                        <tr key={rule.id} className="hover:bg-slate-800/30 transition">
                          <td className="py-3 px-4 font-medium text-white">{rule.name}</td>
                          <td className="py-3 px-4 text-slate-300">{formatMetricLabel(rule.metric)}</td>
                          <td className="py-3 px-4 text-amber-400 font-mono">
                            {formatThresholdDisplay(rule.metric, rule.operator, rule.threshold)}
                          </td>
                          <td className="py-3 px-4 text-slate-400">{formatWindowLabel(rule.window_minutes)}</td>
                          <td className="py-3 px-4 text-slate-400 uppercase text-[10px]">
                            {rule.channel}
                          </td>
                          <td className="py-3 px-4">
                            <button
                              onClick={() => handleToggleActive(rule)}
                              className={`px-2 py-0.5 rounded-full text-[10px] font-medium transition ${
                                rule.is_active
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : "bg-slate-800 text-slate-400 border border-slate-700"
                              }`}
                            >
                              {rule.is_active ? "Enabled" : "Disabled"}
                            </button>
                          </td>
                          <td className="py-3 px-4 text-right space-x-2">
                            <button
                              onClick={() => handleTestRule(rule.id)}
                              disabled={testingRuleId === rule.id}
                              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition disabled:opacity-50"
                            >
                              {testingRuleId === rule.id ? "Testing..." : "Test"}
                            </button>
                            <button
                              onClick={() => openEditModal(rule)}
                              className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 text-[11px] transition"
                            >
                              Edit
                            </button>
                            <button
                              onClick={() => handleDeleteRule(rule.id)}
                              className="px-2 py-1 rounded bg-rose-500/10 hover:bg-rose-500/20 text-rose-400 text-[11px] transition"
                            >
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Fired Alert History Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <h2 className="text-base font-semibold text-white">Alert Incident History</h2>
                <p className="text-xs text-slate-400">Audit log of triggered thresholds and outbound dispatches</p>
              </div>
            </div>

            <div className="bg-slate-900/60 border border-slate-800/80 rounded-xl overflow-hidden shadow-sm">
              {history.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">
                  No alert incidents recorded yet. All systems operating within normal thresholds.
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-slate-950/40 text-slate-400 border-b border-slate-800">
                      <tr>
                        <th className="py-3 px-4 font-medium">Triggered At</th>
                        <th className="py-3 px-4 font-medium">Rule Name</th>
                        <th className="py-3 px-4 font-medium">Metric</th>
                        <th className="py-3 px-4 font-medium">Observed Value</th>
                        <th className="py-3 px-4 font-medium">Threshold</th>
                        <th className="py-3 px-4 font-medium">Delivery</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60">
                      {history.map((h) => (
                        <tr key={h.id} className="hover:bg-slate-800/30 transition">
                          <td className="py-3 px-4 text-slate-400 font-mono text-[11px]">
                            {new Date(h.fired_at).toLocaleString()}
                          </td>
                          <td className="py-3 px-4 font-medium text-white">{h.rule_name || "Rule"}</td>
                          <td className="py-3 px-4 text-slate-300">{formatMetricLabel(h.metric)}</td>
                          <td className="py-3 px-4 text-rose-400 font-mono font-bold">
                            {formatObservedValue(h.metric, h.metric_value)}
                          </td>
                          <td className="py-3 px-4 text-slate-400 font-mono">
                            {formatThresholdDisplay(h.metric, h.operator, h.threshold)}
                          </td>
                          <td className="py-3 px-4">
                            <span
                              className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                                h.notification_status === "delivered"
                                  ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20"
                                  : h.notification_status === "failed"
                                  ? "bg-rose-500/10 text-rose-400 border border-rose-500/20"
                                  : "bg-slate-800 text-slate-400 border border-slate-700"
                              }`}
                            >
                              {h.notification_status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>

          {/* Quick Links / Footer */}
          <div className="flex items-center justify-between pt-4 border-t border-slate-800/80 text-xs text-slate-500">
            <span>TraceHarbor Phase 4 Alert Monitoring Engine</span>
            <div className="flex items-center space-x-4">
              <Link href="/analytics" className="text-slate-400 hover:text-white transition">
                Advanced Analytics →
              </Link>
              <Link href="/runs" className="text-slate-400 hover:text-white transition">
                Runs Explorer →
              </Link>
            </div>
          </div>
        </main>
      </div>

      {/* Create / Edit Rule Modal */}
      {showModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm">
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 max-w-lg w-full space-y-5 shadow-xl">
            <div className="flex items-center justify-between">
              <h3 className="text-base font-semibold text-white">
                {editingRule ? "Edit Alert Rule" : "Create Alert Rule"}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="text-slate-400 hover:text-white transition"
              >
                ✕
              </button>
            </div>

            {formError && (
              <div className="p-3 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
                {formError}
              </div>
            )}

            <form onSubmit={handleSaveRule} className="space-y-4 text-xs">
              {/* Rule Name */}
              <div>
                <label className="block text-slate-400 font-medium mb-1">Rule Name</label>
                <input
                  type="text"
                  value={ruleName}
                  onChange={(e) => setRuleName(e.target.value)}
                  placeholder="e.g., High Error Rate Spike"
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/50"
                  required
                />
              </div>

              {/* Metric & Operator Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Target Metric</label>
                  <select
                    value={ruleMetric}
                    onChange={(e) => setRuleMetric(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/50"
                  >
                    <option value="error_rate">Error Rate (0.0 - 1.0)</option>
                    <option value="p95_latency_ms">p95 Latency (ms)</option>
                    <option value="total_cost">Estimated Cost ($)</option>
                    <option value="eval_pass_rate">Eval Pass Rate (0.0 - 1.0)</option>
                    <option value="regression_count">Regression Count</option>
                  </select>
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Condition Operator</label>
                  <select
                    value={ruleOperator}
                    onChange={(e) => setRuleOperator(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/50"
                  >
                    <option value=">">Greater than (&gt;)</option>
                    <option value=">=">Greater than or equal (&gt;=)</option>
                    <option value="<">Less than (&lt;)</option>
                    <option value="<=">Less than or equal (&lt;=)</option>
                    <option value="==">Equal to (==)</option>
                  </select>
                </div>
              </div>

              {/* Threshold & Window Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Threshold Value</label>
                  <input
                    type="number"
                    step="any"
                    value={ruleThreshold}
                    onChange={(e) => setRuleThreshold(e.target.value)}
                    placeholder="e.g., 0.05 or 1500"
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/50"
                    required
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Evaluation Window</label>
                  <select
                    value={ruleWindowMinutes}
                    onChange={(e) => setRuleWindowMinutes(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/50"
                  >
                    <option value="15">Last 15 Minutes (15m)</option>
                    <option value="60">Last 1 Hour (1h)</option>
                    <option value="360">Last 6 Hours (6h)</option>
                    <option value="1440">Last 24 Hours (24h)</option>
                    <option value="10080">Last 7 Days (7d)</option>
                  </select>
                </div>
              </div>

              {/* Cooldown & Channel Grid */}
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-slate-400 font-medium mb-1">Cooldown (Minutes)</label>
                  <input
                    type="number"
                    min="1"
                    value={ruleCooldown}
                    onChange={(e) => setRuleCooldown(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/50"
                    required
                  />
                </div>

                <div>
                  <label className="block text-slate-400 font-medium mb-1">Notification Channel</label>
                  <select
                    value={ruleChannel}
                    onChange={(e) => setRuleChannel(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/50"
                  >
                    <option value="in_app">In-App Only</option>
                    <option value="webhook">Outbound Webhook Only</option>
                    <option value="both">In-App + Webhook</option>
                  </select>
                </div>
              </div>

              {/* Optional Webhook URL and Secret */}
              {(ruleChannel === "webhook" || ruleChannel === "both") && (
                <div className="space-y-3 pt-2 border-t border-slate-800">
                  <div>
                    <label className="block text-slate-400 font-medium mb-1">
                      Webhook Destination URL (Public HTTPS)
                    </label>
                    <input
                      type="url"
                      value={ruleWebhookUrl}
                      onChange={(e) => setRuleWebhookUrl(e.target.value)}
                      placeholder="https://alerts.yourdomain.com/webhook"
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/50"
                      required
                    />
                    <p className="text-[10px] text-slate-500 mt-1">
                      SSRF Defense Active: Localhost, private RFC1918 subnets, and cloud metadata IPs are blocked.
                    </p>
                  </div>

                  <div>
                    <label className="block text-slate-400 font-medium mb-1">
                      Webhook Signing Secret (Optional)
                    </label>
                    <input
                      type="password"
                      value={ruleWebhookSecret}
                      onChange={(e) => setRuleWebhookSecret(e.target.value)}
                      placeholder={editingRule ? "(Leave blank to keep existing)" : "HMAC SHA-256 secret"}
                      className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-slate-200 focus:outline-none focus:border-emerald-500/50"
                    />
                  </div>
                </div>
              )}

              <div className="flex items-center justify-end space-x-3 pt-4 border-t border-slate-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 transition"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white font-medium transition disabled:opacity-50"
                >
                  {submitting ? "Saving..." : editingRule ? "Save Changes" : "Create Rule"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
