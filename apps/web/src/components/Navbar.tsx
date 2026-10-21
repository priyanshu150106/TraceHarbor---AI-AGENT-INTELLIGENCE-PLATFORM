"use client";

import Link from "next/link";
import React from "react";

export function Navbar({ title = "Observability" }: { title?: string }) {
  return (
    <header className="h-16 border-b border-slate-800/80 bg-slate-900/40 px-6 flex items-center justify-between backdrop-blur shrink-0">
      <div className="flex items-center space-x-3">
        <span className="text-xs uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
          Workspace: default
        </span>
        <span className="text-slate-600">/</span>
        <span className="text-sm font-medium text-slate-300">{title}</span>
      </div>

      <div className="flex items-center space-x-4">
        <a
          href="http://localhost:8000/docs"
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs text-slate-400 hover:text-slate-200 transition flex items-center space-x-1"
        >
          <span>FastAPI Docs</span>
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
        <a
          href="https://github.com/priyanshu150106/TraceHarbor---AI-AGENT-INTELLIGENCE-PLATFORM"
          target="_blank"
          rel="noopener noreferrer"
          className="px-3 py-1.5 text-xs rounded-md bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium transition border border-slate-700 flex items-center space-x-1.5"
        >
          <span>GitHub</span>
        </a>
      </div>
    </header>
  );
}
