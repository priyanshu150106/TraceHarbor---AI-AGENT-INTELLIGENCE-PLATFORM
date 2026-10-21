"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import React, { useEffect, useMemo, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchRunDetail } from "@/lib/api";
import { RunDetail, Span } from "@/lib/types";

export default function TraceDetailPage() {
  const params = useParams();
  const runId = params?.id as string;

  const [run, setRun] = useState<RunDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedSpan, setSelectedSpan] = useState<Span | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [showRawPayloads, setShowRawPayloads] = useState(false);

  const loadRun = React.useCallback(() => {
    if (!runId) return;
    setLoading(true);
    setError(null);
    fetchRunDetail(runId)
      .then((data) => {
        setRun(data);
        if (data.spans.length > 0) {
          setSelectedSpan(data.spans[0]);
        }
      })
      .catch((err) => setError(err.message || "Failed to load trace detail."))
      .finally(() => setLoading(false));
  }, [runId]);

  useEffect(() => {
    loadRun();
  }, [loadRun]);


  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(text);
    setTimeout(() => setCopiedId(null), 1500);
  };

  // Build hierarchical parent-child span structure
  const { rootSpans, childrenMap, totalDurationMs } = useMemo(() => {
    if (!run || !run.spans) {
      return { rootSpans: [], childrenMap: new Map<string, Span[]>(), totalDurationMs: 1 };
    }

    const cMap = new Map<string, Span[]>();
    const roots: Span[] = [];

    const runStart = new Date(run.started_at).getTime();
    let maxEnd = run.ended_at ? new Date(run.ended_at).getTime() : runStart;

    run.spans.forEach((s) => {
      const sStart = new Date(s.started_at).getTime();
      const sEnd = s.ended_at ? new Date(s.ended_at).getTime() : sStart + (s.duration_ms || 0);
      if (sEnd > maxEnd) maxEnd = sEnd;

      if (!s.parent_span_id) {
        roots.push(s);
      } else {
        const existing = cMap.get(s.parent_span_id) || [];
        existing.push(s);
        cMap.set(s.parent_span_id, existing);
      }
    });

    const calculatedDuration = Math.max(1, maxEnd - runStart, run.duration_ms || 1);
    return { rootSpans: roots.length > 0 ? roots : run.spans, childrenMap: cMap, totalDurationMs: calculatedDuration };
  }, [run]);

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title="Trace Inspection" />

        <main className="p-8 space-y-6 flex-1 overflow-y-auto max-w-7xl w-full mx-auto">
          {/* Breadcrumb Navigation */}
          <div className="flex items-center space-x-2 text-xs text-slate-400">
            <Link href="/runs" className="hover:text-slate-200 transition">
              Runs Explorer
            </Link>
            <span>/</span>
            <span className="text-white font-mono">{runId?.slice(0, 8)}...</span>
          </div>

          {/* Loading State */}
          {loading && (
            <div className="py-20 text-center space-y-3">
              <div className="inline-block w-6 h-6 border-2 border-emerald-500 border-t-transparent rounded-full animate-spin"></div>
              <p className="text-xs text-slate-400">Loading trace telemetry and span waterfall...</p>
            </div>
          )}

          {/* Error State */}
          {error && (
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-6 text-center space-y-3">
              <p className="text-sm font-semibold text-rose-300">Trace Not Found or Access Denied</p>
              <p className="text-xs text-slate-400">{error}</p>
              <Link
                href="/runs"
                className="inline-block px-3 py-1.5 text-xs rounded bg-slate-800 text-slate-200 hover:bg-slate-700 transition"
              >
                Back to Runs Explorer
              </Link>
            </div>
          )}

          {/* Trace Content */}
          {!loading && run && (
            <div className="space-y-6">
              {/* Run Header Card */}
              <div className="rounded-xl border border-slate-800 bg-slate-900/60 p-6 space-y-4">
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center space-x-3">
                      <h1 className="text-xl font-bold text-white tracking-tight">
                        {run.name || "Unnamed Agent Execution"}
                      </h1>
                      <span
                        className={`px-2 py-0.5 rounded text-[11px] font-semibold border uppercase tracking-wider ${
                          run.status === "completed"
                            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
                            : run.status === "error"
                            ? "bg-rose-500/10 text-rose-400 border-rose-500/30"
                            : "bg-blue-500/10 text-blue-400 border-blue-500/30"
                        }`}
                      >
                        {run.status}
                      </span>
                    </div>
                    <div className="flex items-center space-x-2 text-xs text-slate-400 font-mono">
                      <span>Run ID: {run.id}</span>
                      <button
                        onClick={() => copyToClipboard(run.id)}
                        className="text-slate-500 hover:text-slate-300 transition"
                        title="Copy Run UUID"
                      >
                        {copiedId === run.id ? (
                          <span className="text-emerald-400 font-sans text-[10px]">Copied!</span>
                        ) : (
                          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  {/* Summary Metric Pills */}
                  <div className="flex flex-wrap items-center gap-2">
                    <div className="px-3 py-1.5 rounded-md bg-slate-950 border border-slate-800 text-xs">
                      <span className="text-slate-400 block text-[10px] uppercase">Duration</span>
                      <span className="font-mono font-semibold text-slate-200">
                        {run.duration_ms !== null ? `${run.duration_ms}ms` : "-"}
                      </span>
                    </div>
                    <div className="px-3 py-1.5 rounded-md bg-slate-950 border border-slate-800 text-xs">
                      <span className="text-slate-400 block text-[10px] uppercase">Total Tokens</span>
                      <span className="font-mono font-semibold text-indigo-400">
                        {run.total_tokens.toLocaleString()}
                      </span>
                    </div>
                    <div className="px-3 py-1.5 rounded-md bg-slate-950 border border-slate-800 text-xs">
                      <span className="text-slate-400 block text-[10px] uppercase">Est. Cost</span>
                      <span className="font-mono font-semibold text-emerald-400">
                        ${Number(run.total_cost_usd).toFixed(5)}
                      </span>
                    </div>
                    <div className="px-3 py-1.5 rounded-md bg-slate-950 border border-slate-800 text-xs">
                      <span className="text-slate-400 block text-[10px] uppercase">Spans</span>
                      <span className="font-mono font-semibold text-slate-300">
                        {run.spans.length}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Error Banner if Run Failed */}
                {run.error && (
                  <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 p-3 text-xs text-rose-300 space-y-1">
                    <p className="font-semibold text-rose-200">Execution Error Caught</p>
                    <pre className="font-mono whitespace-pre-wrap text-[11px] bg-rose-950/30 p-2 rounded">
                      {run.error}
                    </pre>
                  </div>
                )}

                {/* Collapsible Inputs & Outputs */}
                <div className="border-t border-slate-800/80 pt-3">
                  <button
                    onClick={() => setShowRawPayloads(!showRawPayloads)}
                    className="text-xs text-slate-400 hover:text-slate-200 flex items-center space-x-1.5 font-medium transition"
                  >
                    <span>{showRawPayloads ? "▼ Hide" : "▶ Show"} Agent Inputs & Outputs</span>
                  </button>

                  {showRawPayloads && (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-3">
                      <div className="space-y-1">
                        <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Input Payload</span>
                        <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-48 whitespace-pre-wrap">
                          {run.input ? JSON.stringify(run.input, null, 2) : "None"}
                        </pre>
                      </div>
                      <div className="space-y-1">
                        <span className="text-[10px] font-medium text-slate-400 uppercase tracking-wider">Output Result</span>
                        <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-48 whitespace-pre-wrap">
                          {run.output ? JSON.stringify(run.output, null, 2) : "None"}
                        </pre>
                      </div>
                    </div>
                  )}
                </div>
              </div>

              {/* Main Trace Split View: Waterfall / Tree on Left, Span Details Inspector on Right */}
              <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
                {/* Left: Waterfall & Hierarchy Timeline (7 columns) */}
                <div className="lg:col-span-7 rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h2 className="text-sm font-semibold text-white">Execution Waterfall</h2>
                      <p className="text-[11px] text-slate-400">
                        Timeline and hierarchical sequence of tool and LLM spans.
                      </p>
                    </div>
                    <span className="text-xs font-mono text-slate-400">
                      Total: {run.duration_ms || totalDurationMs}ms
                    </span>
                  </div>

                  {/* Waterfall Header Axis */}
                  <div className="border-b border-slate-800 pb-2 text-[10px] text-slate-500 font-mono flex justify-between">
                    <span>0ms</span>
                    <span>{Math.round(totalDurationMs * 0.25)}ms</span>
                    <span>{Math.round(totalDurationMs * 0.5)}ms</span>
                    <span>{Math.round(totalDurationMs * 0.75)}ms</span>
                    <span>{Math.round(totalDurationMs)}ms</span>
                  </div>

                  {/* Waterfall & Tree Rows */}
                  <div className="space-y-1.5 pt-1">
                    {rootSpans.map((span) => (
                      <SpanWaterfallItem
                        key={span.id}
                        span={span}
                        runStartedAt={new Date(run.started_at).getTime()}
                        totalDurationMs={totalDurationMs}
                        childrenMap={childrenMap}
                        level={0}
                        selectedSpanId={selectedSpan?.id}
                        onSelect={(s) => setSelectedSpan(s)}
                      />
                    ))}
                  </div>
                </div>

                {/* Right: Span Detail Inspector (5 columns) */}
                <div className="lg:col-span-5 rounded-xl border border-slate-800 bg-slate-900/60 p-5 space-y-4 sticky top-6">
                  {selectedSpan ? (
                    <div className="space-y-4">
                      <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                        <div>
                          <span className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
                            Span Inspector
                          </span>
                          <h3 className="text-base font-bold text-white break-all">
                            {selectedSpan.name}
                          </h3>
                        </div>
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-medium border uppercase ${
                            selectedSpan.status === "completed"
                              ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                              : selectedSpan.status === "error"
                              ? "bg-rose-500/10 text-rose-400 border-rose-500/20"
                              : "bg-blue-500/10 text-blue-400 border-blue-500/20"
                          }`}
                        >
                          {selectedSpan.status}
                        </span>
                      </div>

                      {/* Span Metadata Grid */}
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="bg-slate-950 p-2.5 rounded border border-slate-800/80">
                          <span className="text-slate-500 text-[10px] block uppercase">Type</span>
                          <span className="font-medium text-slate-200 capitalize">{selectedSpan.span_type}</span>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded border border-slate-800/80">
                          <span className="text-slate-500 text-[10px] block uppercase">Duration</span>
                          <span className="font-mono font-medium text-slate-200">
                            {selectedSpan.duration_ms !== null ? `${selectedSpan.duration_ms}ms` : "-"}
                          </span>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded border border-slate-800/80">
                          <span className="text-slate-500 text-[10px] block uppercase">Model</span>
                          <span className="font-mono font-medium text-slate-200">
                            {selectedSpan.model || "None"}
                          </span>
                        </div>
                        <div className="bg-slate-950 p-2.5 rounded border border-slate-800/80">
                          <span className="text-slate-500 text-[10px] block uppercase">Tokens</span>
                          <span className="font-mono font-medium text-indigo-400">
                            {selectedSpan.total_tokens.toLocaleString()}
                          </span>
                        </div>
                      </div>

                      {/* Error details if span failed */}
                      {selectedSpan.error && (
                        <div className="p-3 rounded bg-rose-500/10 border border-rose-500/30 text-xs text-rose-300 space-y-1">
                          <span className="font-semibold text-rose-200">Span Error:</span>
                          <pre className="font-mono text-[11px] whitespace-pre-wrap bg-rose-950/40 p-2 rounded">
                            {selectedSpan.error}
                          </pre>
                        </div>
                      )}

                      {/* Input Inspector */}
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                          Input
                        </span>
                        <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-40 whitespace-pre-wrap">
                          {selectedSpan.input ? JSON.stringify(selectedSpan.input, null, 2) : "None"}
                        </pre>
                      </div>

                      {/* Output Inspector */}
                      <div className="space-y-1">
                        <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                          Output
                        </span>
                        <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-300 overflow-x-auto max-h-40 whitespace-pre-wrap">
                          {selectedSpan.output ? JSON.stringify(selectedSpan.output, null, 2) : "None"}
                        </pre>
                      </div>

                      {/* Metadata Inspector */}
                      {selectedSpan.metadata && Object.keys(selectedSpan.metadata).length > 0 && (
                        <div className="space-y-1">
                          <span className="text-[10px] uppercase tracking-wider text-slate-400 font-semibold">
                            Metadata
                          </span>
                          <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800 text-xs font-mono text-slate-400 overflow-x-auto max-h-32 whitespace-pre-wrap">
                            {JSON.stringify(selectedSpan.metadata, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  ) : (
                    <div className="py-16 text-center text-xs text-slate-500">
                      Select a span from the waterfall timeline to inspect its inputs, outputs, tokens, and errors.
                    </div>
                  )}
                </div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
}

/**
 * Individual waterfall row showing span indentation, type badge, duration,
 * and a proportional timeline bar.
 */
function SpanWaterfallItem({
  span,
  runStartedAt,
  totalDurationMs,
  childrenMap,
  level = 0,
  selectedSpanId,
  onSelect,
}: {
  span: Span;
  runStartedAt: number;
  totalDurationMs: number;
  childrenMap: Map<string, Span[]>;
  level: number;
  selectedSpanId?: string;
  onSelect: (span: Span) => void;
}) {
  const children = childrenMap.get(span.id) || [];
  const isSelected = selectedSpanId === span.id;

  // Calculate timeline bar offsets
  const spanStart = new Date(span.started_at).getTime();
  const offsetMs = Math.max(0, spanStart - runStartedAt);
  const offsetPct = Math.min(100, Math.max(0, (offsetMs / totalDurationMs) * 100));

  const durationMs = span.duration_ms || 1;
  const widthPct = Math.max(1.5, Math.min(100 - offsetPct, (durationMs / totalDurationMs) * 100));

  const typeColorMap: Record<string, string> = {
    agent: "bg-indigo-500/10 text-indigo-400 border-indigo-500/30",
    tool: "bg-emerald-500/10 text-emerald-400 border-emerald-500/30",
    llm: "bg-violet-500/10 text-violet-400 border-violet-500/30",
    retrieval: "bg-amber-500/10 text-amber-400 border-amber-500/30",
    custom: "bg-slate-500/10 text-slate-400 border-slate-500/30",
  };

  const barColor =
    span.status === "error"
      ? "bg-rose-500"
      : span.span_type === "tool"
      ? "bg-emerald-500"
      : span.span_type === "llm"
      ? "bg-violet-500"
      : "bg-indigo-500";

  return (
    <div className="space-y-1">
      <div
        onClick={() => onSelect(span)}
        className={`flex items-center justify-between p-2 rounded-lg cursor-pointer transition border text-xs ${
          isSelected
            ? "bg-slate-800/80 border-emerald-500/40 shadow-sm"
            : "bg-slate-950/40 border-slate-800/60 hover:bg-slate-800/30"
        }`}
      >
        {/* Left: Span Name and Type */}
        <div className="flex items-center space-x-2 min-w-0 pr-2" style={{ paddingLeft: `${level * 16}px` }}>
          {level > 0 && <span className="text-slate-600 select-none">└─</span>}
          <span
            className={`px-1.5 py-0.5 rounded text-[9px] font-mono uppercase border ${
              typeColorMap[span.span_type] || "bg-slate-800 text-slate-300"
            }`}
          >
            {span.span_type}
          </span>
          <span className="font-medium text-slate-200 truncate">{span.name}</span>
          {span.model && (
            <span className="text-[10px] font-mono text-slate-500 truncate hidden sm:inline">
              ({span.model})
            </span>
          )}
        </div>

        {/* Right: Waterfall Bar Graphic & Duration */}
        <div className="flex items-center space-x-3 w-40 sm:w-56 shrink-0">
          <div className="relative w-full h-2 bg-slate-900 rounded overflow-hidden">
            <div
              className={`absolute top-0 bottom-0 rounded ${barColor} transition-all`}
              style={{
                left: `${offsetPct}%`,
                width: `${widthPct}%`,
              }}
            />
          </div>
          <span className="font-mono text-[11px] text-slate-400 w-12 text-right shrink-0">
            {span.duration_ms !== null ? `${span.duration_ms}ms` : "-"}
          </span>
        </div>
      </div>

      {/* Nested Children */}
      {children.map((child) => (
        <SpanWaterfallItem
          key={child.id}
          span={child}
          runStartedAt={runStartedAt}
          totalDurationMs={totalDurationMs}
          childrenMap={childrenMap}
          level={level + 1}
          selectedSpanId={selectedSpanId}
          onSelect={onSelect}
        />
      ))}
    </div>
  );
}
