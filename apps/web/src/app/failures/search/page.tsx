"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import React, { Suspense, useCallback, useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { searchSimilarFailures } from "@/lib/api";
import { SimilarFailureItem } from "@/lib/types";

function SimilarFailuresSearchContent() {
  const searchParams = useSearchParams();
  const initialEventId = searchParams?.get("event_id") || "";

  const [queryText, setQueryText] = useState("");
  const [eventId, setEventId] = useState(initialEventId);
  const [threshold, setThreshold] = useState(0.65);
  const [results, setResults] = useState<SimilarFailureItem[]>([]);
  const [searchMethod, setSearchMethod] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [searched, setSearched] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const executeSearch = useCallback(
    async (targetQuery: string, targetEventId: string, currentThreshold: number) => {
      if (!targetQuery.trim() && !targetEventId.trim()) {
        setError("Please provide either an error text query or a failure event ID.");
        return;
      }

      setLoading(true);
      setError(null);
      try {
        const res = await searchSimilarFailures({
          query_text: targetQuery.trim() || undefined,
          event_id: targetEventId.trim() || undefined,
          threshold: currentThreshold,
          limit: 25,
        });
        setResults(res.results);
        setSearchMethod(res.search_method);
        setSearched(true);
      } catch (err: any) {
        setError(err.message || "Similarity search failed.");
      } finally {
        setLoading(false);
      }
    },
    []
  );

  const handleSearch = (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    executeSearch(queryText, eventId, threshold);
  };

  useEffect(() => {
    if (initialEventId) {
      setEventId(initialEventId);
      executeSearch("", initialEventId, threshold);
    }
  }, [initialEventId, executeSearch, threshold]);

  return (
    <main className="flex-1 overflow-y-auto p-6 space-y-6">
      {/* Header */}
      <div>
        <div className="flex items-center gap-2">
          <Link href="/failures" className="text-slate-400 hover:text-white text-sm transition">
            ← Failure Intelligence
          </Link>
          <span className="text-slate-600">/</span>
          <h1 className="text-2xl font-bold tracking-tight text-white">Find Similar Failures</h1>
        </div>
        <p className="text-sm text-slate-400 mt-1">
          Nearest-neighbor vector search against normalized error embeddings using PostgreSQL pgvector.
        </p>
      </div>

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/30 text-rose-300 text-sm">
          {error}
        </div>
      )}

      {/* Search Input Card */}
      <form onSubmit={handleSearch} className="bg-slate-900/60 border border-slate-800 rounded-xl p-6 space-y-4 shadow-sm">
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-300 mb-1">
              Query Error Text
            </label>
            <textarea
              rows={3}
              placeholder="Paste raw error message, stack trace fragment, or failure summary to find similar incidents..."
              value={queryText}
              onChange={(e) => {
                setQueryText(e.target.value);
                if (e.target.value) setEventId("");
              }}
              className="w-full px-3.5 py-2.5 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono transition"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1">
                Or Search by Existing Event ID
              </label>
              <input
                type="text"
                placeholder="UUID of failure event"
                value={eventId}
                onChange={(e) => {
                  setEventId(e.target.value);
                  if (e.target.value) setQueryText("");
                }}
                className="w-full px-3.5 py-2 text-xs bg-slate-950 border border-slate-800 rounded-lg text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500 font-mono transition"
              />
            </div>

            <div>
              <div className="flex items-center justify-between text-xs font-medium text-slate-300 mb-1">
                <span>Similarity Threshold</span>
                <span className="font-mono text-emerald-400 font-bold">{Math.round(threshold * 100)}%</span>
              </div>
              <input
                type="range"
                min="0.30"
                max="0.95"
                step="0.05"
                value={threshold}
                onChange={(e) => setThreshold(parseFloat(e.target.value))}
                className="w-full mt-2"
              />
              <div className="flex justify-between text-[11px] text-slate-500 mt-0.5">
                <span>30% (Loose)</span>
                <span>65% (Recommended)</span>
                <span>95% (Near Identical)</span>
              </div>
            </div>
          </div>
        </div>

        <div className="flex justify-end pt-2">
          <button
            type="submit"
            disabled={loading}
            className="px-5 py-2.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50 transition shadow flex items-center gap-2"
          >
            {loading ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                Searching Vector Index...
              </>
            ) : (
              "Search Similar Failures"
            )}
          </button>
        </div>
      </form>

      {/* Results Section */}
      {searched && (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <h2 className="text-base font-semibold text-white">Search Results</h2>
              <span className="text-xs text-slate-400">({results.length} matches found)</span>
            </div>

            {searchMethod && (
              <div>
                {searchMethod === "vector_similarity" ? (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    pgvector Semantic Similarity
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/30">
                    Lexical Fallback (Token Jaccard)
                  </span>
                )}
              </div>
            )}
          </div>

          {results.length === 0 ? (
            <div className="bg-slate-900/40 border border-slate-800 rounded-xl p-12 text-center text-slate-400 text-sm space-y-2">
              <p>No failure events met the {Math.round(threshold * 100)}% similarity threshold.</p>
              <p className="text-xs text-slate-500">Try lowering the similarity threshold slider above to expand candidate matches.</p>
            </div>
          ) : (
            <div className="space-y-3">
              {results.map((match) => (
                <div
                  key={match.event_id}
                  className="bg-slate-900/60 border border-slate-800 rounded-xl p-4 shadow-sm hover:border-slate-700 transition space-y-3"
                >
                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="px-2 py-0.5 rounded text-xs font-semibold bg-slate-800 text-slate-200 uppercase">
                        {match.severity}
                      </span>
                      <span className="text-xs font-mono text-slate-400">
                        {match.failure_category}
                      </span>
                      {match.agent_name && (
                        <span className="text-xs text-slate-300">
                          {match.agent_name} {match.agent_version && `v${match.agent_version}`}
                        </span>
                      )}
                    </div>

                    {/* Similarity score meter */}
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-bold text-emerald-400 font-mono">
                        {Math.round(match.similarity_score * 100)}% Match
                      </span>
                      <div className="w-24 bg-slate-800 h-2 rounded-full overflow-hidden">
                        <div
                          className="bg-emerald-500 h-full rounded-full transition-all"
                          style={{ width: `${Math.min(100, Math.round(match.similarity_score * 100))}%` }}
                        />
                      </div>
                    </div>
                  </div>

                  {/* Sanitized error snippet */}
                  <pre className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 text-xs font-mono text-slate-200 whitespace-pre-wrap line-clamp-3">
                    {match.error_summary}
                  </pre>

                  {/* Footer actions */}
                  <div className="flex items-center justify-between pt-1 text-xs text-slate-400">
                    <span>Occurred: {new Date(match.occurred_at).toLocaleString()}</span>
                    <div className="flex items-center gap-3">
                      {match.cluster_id && (
                        <Link
                          href={`/failures/clusters/${match.cluster_id}`}
                          className="text-emerald-400 hover:text-emerald-300 underline"
                        >
                          View Cluster →
                        </Link>
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

export default function SimilarFailuresSearchPage() {
  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 antialiased overflow-hidden">
      <Sidebar />
      <div className="flex flex-col flex-1 overflow-hidden">
        <Navbar />
        <Suspense fallback={<div className="p-12 text-slate-400 text-sm">Loading search interface...</div>}>
          <SimilarFailuresSearchContent />
        </Suspense>
      </div>
    </div>
  );
}
