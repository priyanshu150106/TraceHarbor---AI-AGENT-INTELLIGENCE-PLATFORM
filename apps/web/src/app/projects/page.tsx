"use client";

import Link from "next/link";
import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import { fetchProjects } from "@/lib/api";
import { Project } from "@/lib/types";

export default function ProjectsPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadProjects = () => {
    setLoading(true);
    setError(null);
    fetchProjects()
      .then((data) => setProjects(data))
      .catch((err) => setError(err.message || "Failed to load projects."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadProjects();
  }, []);

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title="Projects" />

        <main className="p-8 space-y-6 flex-1 overflow-y-auto max-w-6xl w-full mx-auto">
          {/* Header */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white">Active Projects</h1>
              <p className="text-xs text-slate-400 mt-1">
                Logical grouping for agent traces, datasets, and API key authorization.
              </p>
            </div>
            <button
              onClick={loadProjects}
              disabled={loading}
              className="px-3 py-1.5 text-xs rounded-md bg-slate-800 hover:bg-slate-700 text-slate-300 transition border border-slate-700 flex items-center space-x-1.5 self-start disabled:opacity-50"
            >
              <svg className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
              </svg>
              <span>Refresh</span>
            </button>
          </div>

          {/* Error Banner */}
          {error && (
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-4 text-xs text-amber-300">
              <p className="font-semibold text-amber-200">Unable to load projects</p>
              <p>{error}</p>
            </div>
          )}

          {/* Projects Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {loading ? (
              <div className="col-span-2 py-16 text-center text-xs text-slate-500">
                Loading project records...
              </div>
            ) : projects.length === 0 ? (
              <div className="col-span-2 rounded-xl border border-slate-800 bg-slate-900/40 p-8 text-center space-y-3">
                <p className="text-sm font-semibold text-slate-300">No Projects Found</p>
                <p className="text-xs text-slate-500">
                  Projects are automatically populated from the database or created during agent onboarding.
                </p>
              </div>
            ) : (
              projects.map((project) => (
                <div
                  key={project.id}
                  className="rounded-xl border border-slate-800 bg-slate-900/50 p-5 space-y-4 hover:border-slate-700 transition"
                >
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center space-x-2">
                        <span className="h-2 w-2 rounded-full bg-emerald-400"></span>
                        <h3 className="font-semibold text-sm text-white">{project.name}</h3>
                      </div>
                      <p className="text-xs text-slate-400">
                        {project.description || "No description provided."}
                      </p>
                    </div>
                    <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-slate-800 text-slate-300 border border-slate-700">
                      {project.runs_count} {project.runs_count === 1 ? "run" : "runs"}
                    </span>
                  </div>

                  <div className="border-t border-slate-800/80 pt-3 flex items-center justify-between text-xs text-slate-500">
                    <span className="font-mono text-[11px]">ID: {project.id.slice(0, 8)}...</span>
                    <span>Created: {new Date(project.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              ))
            )}
          </div>

          {/* Architecture & Security Notice */}
          <div className="rounded-lg border border-slate-800/80 bg-slate-900/30 p-5 text-xs text-slate-400 space-y-2">
            <p className="font-semibold text-slate-300">Security & Key Management Contract</p>
            <p>
              TraceHarbor adheres strictly to zero-trust secret protection. Full API keys are generated with high-entropy bytes (<code className="text-slate-300">th_live_...</code>) and shown only once upon generation. Only cryptographic SHA-256 hashes are persisted in the database, ensuring raw keys are never exposed in browser payloads or database dumps.
            </p>
          </div>
        </main>
      </div>
    </div>
  );
}
