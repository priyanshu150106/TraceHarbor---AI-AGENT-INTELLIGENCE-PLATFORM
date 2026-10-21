"use client";

import React, { useEffect, useState } from "react";
import { Navbar } from "@/components/Navbar";
import { Sidebar } from "@/components/Sidebar";
import {
  createDataset,
  deleteDataset,
  fetchDatasetDetail,
  fetchDatasets,
  uploadDataset,
} from "@/lib/api";
import { DatasetDetail, DatasetSummary, TestCase } from "@/lib/types";

export default function DatasetsPage() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [totalDatasets, setTotalDatasets] = useState(0);

  // Modals state
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [previewDataset, setPreviewDataset] = useState<DatasetDetail | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);

  // Create form state
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [initialInput, setInitialInput] = useState("");
  const [initialExpected, setInitialExpected] = useState("");
  const [initialKeywords, setInitialKeywords] = useState("");
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // Upload form state
  const [uploadName, setUploadName] = useState("");
  const [uploadDesc, setUploadDesc] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [uploadTab, setUploadTab] = useState<"json" | "csv">("json");

  const loadDatasets = (p: number = page, q: string = search) => {
    setLoading(true);
    setError(null);
    fetchDatasets({ page: p, pageSize: 12, search: q })
      .then((res) => {
        setDatasets(res.items);
        setTotalPages(res.total_pages || 1);
        setTotalDatasets(res.total);
      })
      .catch((err) => setError(err.message || "Failed to load datasets."))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadDatasets(1, search);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    loadDatasets(1, search);
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newName.trim()) return;
    setCreating(true);
    setCreateError(null);

    const cases = initialInput.trim()
      ? [
          {
            input: initialInput.trim(),
            expected_output: initialExpected.trim() || null,
            criteria: initialKeywords.trim()
              ? { required_keywords: initialKeywords.split(",").map((k) => k.trim()) }
              : null,
          },
        ]
      : [];

    try {
      await createDataset({
        name: newName.trim(),
        description: newDesc.trim() || undefined,
        cases,
      });
      setShowCreateModal(false);
      setNewName("");
      setNewDesc("");
      setInitialInput("");
      setInitialExpected("");
      setInitialKeywords("");
      loadDatasets(1);
    } catch (err: any) {
      setCreateError(err.message || "Failed to create dataset.");
    } finally {
      setCreating(false);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !uploadName.trim()) {
      setUploadError("Please provide a dataset name and select a file.");
      return;
    }
    setUploading(true);
    setUploadError(null);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("name", uploadName.trim());
    if (uploadDesc.trim()) {
      formData.append("description", uploadDesc.trim());
    }

    try {
      await uploadDataset(formData);
      setShowUploadModal(false);
      setUploadName("");
      setUploadDesc("");
      setSelectedFile(null);
      loadDatasets(1);
    } catch (err: any) {
      setUploadError(err.message || "Upload failed.");
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to delete dataset "${name}"? All associated test cases and experiments will be removed.`)) {
      return;
    }
    try {
      await deleteDataset(id);
      loadDatasets();
    } catch (err: any) {
      alert(err.message || "Failed to delete dataset.");
    }
  };

  const openPreview = async (datasetId: string) => {
    setPreviewLoading(true);
    try {
      const detail = await fetchDatasetDetail(datasetId, 1, 100);
      setPreviewDataset(detail);
    } catch (err: any) {
      alert(err.message || "Failed to load dataset details.");
    } finally {
      setPreviewLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <Sidebar />

      <div className="flex-1 flex flex-col min-w-0">
        <Navbar title="Evaluation Datasets" />

        <main className="p-8 space-y-8 flex-1 overflow-y-auto max-w-7xl w-full mx-auto">
          {/* Header Action Bar */}
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-white flex items-center space-x-2">
                <span>Evaluation Datasets</span>
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-medium">
                  {totalDatasets} Datasets
                </span>
              </h1>
              <p className="text-xs text-slate-400 mt-1">
                Manage test cases, golden answers, and evaluation criteria for automated agent benchmarks.
              </p>
            </div>

            <div className="flex items-center space-x-3">
              <button
                onClick={() => setShowUploadModal(true)}
                className="px-3.5 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 transition flex items-center space-x-1.5"
              >
                <svg className="w-4 h-4 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
                </svg>
                <span>Upload CSV / JSON</span>
              </button>

              <button
                onClick={() => setShowCreateModal(true)}
                className="px-3.5 py-2 text-xs font-semibold rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition shadow-sm flex items-center space-x-1.5"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2.5} d="M12 4v16m8-8H4" />
                </svg>
                <span>Create Dataset</span>
              </button>
            </div>
          </div>

          {/* Search bar */}
          <form onSubmit={handleSearch} className="flex gap-3">
            <div className="relative flex-1">
              <input
                type="text"
                placeholder="Search datasets by title..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-emerald-500"
              />
              <svg className="w-4 h-4 text-slate-500 absolute left-3 top-2.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <button
              type="submit"
              className="px-4 py-2 text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg border border-slate-700 transition"
            >
              Search
            </button>
          </form>

          {/* Error Message */}
          {error && (
            <div className="p-4 rounded-lg bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
              <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              <span>{error}</span>
            </div>
          )}

          {/* Datasets Grid */}
          {loading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="h-44 rounded-xl bg-slate-900/40 border border-slate-800 animate-pulse" />
              ))}
            </div>
          ) : datasets.length === 0 ? (
            <div className="p-12 text-center rounded-xl bg-slate-900/40 border border-slate-800 space-y-4">
              <div className="h-12 w-12 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center mx-auto">
                <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 7v10c0 2 1.5 3 3.5 3h9c2 0 3.5-1 3.5-3V7c0-2-1.5-3-3.5-3h-9C5.5 4 4 5 4 7zM9 9h6M9 13h6M9 17h4" />
                </svg>
              </div>
              <div>
                <h3 className="text-sm font-semibold text-white">No Datasets Found</h3>
                <p className="text-xs text-slate-400 mt-1 max-w-sm mx-auto">
                  Create your first evaluation dataset or upload the example <code className="text-emerald-400 font-mono">datasets/support_agent_golden.json</code> file to evaluate your agents.
                </p>
              </div>
              <div className="pt-2 flex justify-center space-x-3">
                <button
                  onClick={() => setShowUploadModal(true)}
                  className="px-4 py-2 text-xs font-medium rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition"
                >
                  Upload support_agent_golden.json
                </button>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {datasets.map((d) => (
                <div
                  key={d.id}
                  className="p-5 rounded-xl bg-slate-900/60 border border-slate-800/80 hover:border-slate-700 transition flex flex-col justify-between space-y-4 shadow-sm"
                >
                  <div className="space-y-2">
                    <div className="flex items-start justify-between gap-2">
                      <h3 className="font-semibold text-white text-sm tracking-tight">{d.name}</h3>
                      <button
                        onClick={() => handleDelete(d.id, d.name)}
                        className="text-slate-500 hover:text-rose-400 transition p-1"
                        title="Delete Dataset"
                      >
                        <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                        </svg>
                      </button>
                    </div>
                    <p className="text-xs text-slate-400 line-clamp-2">
                      {d.description || "No description provided."}
                    </p>
                  </div>

                  <div className="space-y-3 pt-3 border-t border-slate-800/60">
                    <div className="flex items-center justify-between text-xs text-slate-400">
                      <span className="flex items-center space-x-1.5">
                        <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                        <span className="font-mono text-slate-300 font-medium">{d.test_cases_count} cases</span>
                      </span>
                      <span className="font-mono text-[11px] text-slate-500">
                        {d.experiments_count} experiments
                      </span>
                    </div>

                    <div className="flex items-center justify-between pt-1">
                      <span className="text-[10px] text-slate-500 font-mono">
                        {new Date(d.created_at).toLocaleDateString()}
                      </span>
                      <button
                        onClick={() => openPreview(d.id)}
                        className="text-xs font-medium text-emerald-400 hover:text-emerald-300 transition flex items-center space-x-1"
                      >
                        <span>View Cases</span>
                        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                        </svg>
                      </button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between pt-4 border-t border-slate-800 text-xs text-slate-400">
              <span>
                Page {page} of {totalPages}
              </span>
              <div className="flex space-x-2">
                <button
                  disabled={page <= 1}
                  onClick={() => {
                    const p = page - 1;
                    setPage(p);
                    loadDatasets(p);
                  }}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40"
                >
                  Previous
                </button>
                <button
                  disabled={page >= totalPages}
                  onClick={() => {
                    const p = page + 1;
                    setPage(p);
                    loadDatasets(p);
                  }}
                  className="px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 disabled:opacity-40"
                >
                  Next
                </button>
              </div>
            </div>
          )}
        </main>
      </div>

      {/* CREATE DATASET MODAL */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-base font-bold text-white">Create New Dataset</h2>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-slate-400 hover:text-white text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleCreateSubmit} className="space-y-4">
              {createError && (
                <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                  {createError}
                </div>
              )}

              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Dataset Name *</label>
                <input
                  type="text"
                  required
                  placeholder="e.g., Customer Support Golden Set"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Description (Optional)</label>
                <textarea
                  rows={2}
                  placeholder="Purpose of this benchmark dataset..."
                  value={newDesc}
                  onChange={(e) => setNewDesc(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                />
              </div>

              <div className="p-3 rounded-lg bg-slate-950/60 border border-slate-800/80 space-y-3">
                <span className="text-[11px] font-semibold text-emerald-400 uppercase tracking-wider block">
                  Add Initial Test Case (Optional)
                </span>
                <div className="space-y-1">
                  <label className="text-[11px] text-slate-400">Prompt / Question</label>
                  <input
                    type="text"
                    placeholder="What is the return policy?"
                    value={initialInput}
                    onChange={(e) => setInitialInput(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] text-slate-400">Expected Output</label>
                  <input
                    type="text"
                    placeholder="Returns are accepted within 30 days."
                    value={initialExpected}
                    onChange={(e) => setInitialExpected(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-[11px] text-slate-400">Required Keywords (comma-separated)</label>
                  <input
                    type="text"
                    placeholder="30 days, refund"
                    value={initialKeywords}
                    onChange={(e) => setInitialKeywords(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded px-2.5 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              <div className="flex justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowCreateModal(false)}
                  className="px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={creating}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition disabled:opacity-50"
                >
                  {creating ? "Creating..." : "Create Dataset"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* UPLOAD DATASET MODAL */}
      {showUploadModal && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-xl w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-base font-bold text-white flex items-center space-x-2">
                <span>Upload Dataset File</span>
                <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                  JSON / CSV
                </span>
              </h2>
              <button
                onClick={() => setShowUploadModal(false)}
                className="text-slate-400 hover:text-white text-lg"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleUploadSubmit} className="space-y-4">
              {uploadError && (
                <div className="p-3 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
                  {uploadError}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Dataset Name *</label>
                  <input
                    type="text"
                    required
                    placeholder="e.g., Support Golden Benchmarks"
                    value={uploadName}
                    onChange={(e) => setUploadName(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
                <div className="space-y-1">
                  <label className="text-xs font-medium text-slate-300">Description</label>
                  <input
                    type="text"
                    placeholder="Optional notes"
                    value={uploadDesc}
                    onChange={(e) => setUploadDesc(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-emerald-500"
                  />
                </div>
              </div>

              {/* File Input */}
              <div className="space-y-1">
                <label className="text-xs font-medium text-slate-300">Select File (max 5 MB, up to 500 cases)</label>
                <div className="border-2 border-dashed border-slate-800 hover:border-slate-700 rounded-xl p-5 text-center transition bg-slate-950/40">
                  <input
                    type="file"
                    accept=".json,.csv"
                    required
                    onChange={(e) => {
                      if (e.target.files && e.target.files[0]) {
                        setSelectedFile(e.target.files[0]);
                        if (!uploadName) {
                          setUploadName(e.target.files[0].name.replace(/\.[^/.]+$/, ""));
                        }
                      }
                    }}
                    className="hidden"
                    id="file-upload"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer space-y-2 block">
                    <svg className="w-8 h-8 text-emerald-400 mx-auto" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
                    </svg>
                    <span className="text-xs text-slate-300 font-medium block">
                      {selectedFile ? selectedFile.name : "Click to select a .JSON or .CSV dataset file"}
                    </span>
                    <span className="text-[10px] text-slate-500 block">
                      Enforces UTF-8 encoding, structural validation, and SQL/code isolation
                    </span>
                  </label>
                </div>
              </div>

              {/* Supported Format Preview */}
              <div className="p-3 rounded-lg bg-slate-950 border border-slate-800/80 space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-slate-400 font-medium">Format Reference:</span>
                  <div className="flex space-x-2">
                    <button
                      type="button"
                      onClick={() => setUploadTab("json")}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                        uploadTab === "json" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "text-slate-500"
                      }`}
                    >
                      JSON
                    </button>
                    <button
                      type="button"
                      onClick={() => setUploadTab("csv")}
                      className={`px-2 py-0.5 rounded text-[10px] font-mono ${
                        uploadTab === "csv" ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" : "text-slate-500"
                      }`}
                    >
                      CSV
                    </button>
                  </div>
                </div>

                {uploadTab === "json" ? (
                  <pre className="text-[11px] font-mono text-slate-400 bg-slate-900/60 p-2.5 rounded overflow-x-auto">
{`[
  {
    "input": "What is the return policy?",
    "expected_output": "Returns accepted within 30 days.",
    "criteria": { "required_keywords": ["30 days"] }
  }
]`}
                  </pre>
                ) : (
                  <pre className="text-[11px] font-mono text-slate-400 bg-slate-900/60 p-2.5 rounded overflow-x-auto">
{`input,expected_output,criteria,tags
"What is return policy?","Returns accepted within 30 days.","{""required_keywords"": [""30 days""]}","faq,returns"`}
                  </pre>
                )}
              </div>

              <div className="flex justify-end space-x-3 pt-3">
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="px-3.5 py-2 text-xs font-medium text-slate-400 hover:text-white"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={uploading || !selectedFile}
                  className="px-4 py-2 text-xs font-semibold rounded-lg bg-emerald-500 hover:bg-emerald-400 text-slate-950 transition disabled:opacity-50"
                >
                  {uploading ? "Parsing & Uploading..." : "Upload & Validate"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* TEST CASES PREVIEW MODAL */}
      {previewDataset && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl max-w-4xl w-full p-6 space-y-4 shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <div>
                <h2 className="text-base font-bold text-white flex items-center space-x-2">
                  <span>{previewDataset.name}</span>
                  <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 font-mono">
                    {previewDataset.test_cases_count} Cases
                  </span>
                </h2>
                <p className="text-xs text-slate-400 mt-0.5">{previewDataset.description || "No description."}</p>
              </div>
              <button
                onClick={() => setPreviewDataset(null)}
                className="text-slate-400 hover:text-white text-lg"
              >
                ✕
              </button>
            </div>

            <div className="flex-1 overflow-y-auto space-y-3">
              {previewDataset.test_cases.length === 0 ? (
                <p className="text-xs text-slate-500 text-center py-8">No test cases in this dataset.</p>
              ) : (
                <div className="border border-slate-800 rounded-lg overflow-hidden">
                  <table className="w-full text-left text-xs">
                    <thead className="bg-slate-950 text-slate-400 uppercase font-mono text-[10px] border-b border-slate-800">
                      <tr>
                        <th className="py-2.5 px-4 w-12">#</th>
                        <th className="py-2.5 px-4">Test Input Prompt</th>
                        <th className="py-2.5 px-4">Expected Reference Output</th>
                        <th className="py-2.5 px-4">Evaluation Criteria</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-800/60 bg-slate-900/40 font-mono text-[11px]">
                      {previewDataset.test_cases.map((tc, idx) => (
                        <tr key={tc.id} className="hover:bg-slate-800/30 transition">
                          <td className="py-3 px-4 text-slate-500">{idx + 1}</td>
                          <td className="py-3 px-4 text-slate-200 font-sans text-xs max-w-xs break-words">
                            {typeof tc.input === "string" ? tc.input : JSON.stringify(tc.input)}
                          </td>
                          <td className="py-3 px-4 text-slate-400 font-sans text-xs max-w-xs break-words">
                            {tc.expected_output ? (typeof tc.expected_output === "string" ? tc.expected_output : JSON.stringify(tc.expected_output)) : <span className="text-slate-600 italic">None specified</span>}
                          </td>
                          <td className="py-3 px-4 text-emerald-400">
                            {tc.criteria ? (
                              <pre className="text-[10px] whitespace-pre-wrap break-all">
                                {JSON.stringify(tc.criteria, null, 1)}
                              </pre>
                            ) : (
                              <span className="text-slate-600 italic">Default</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            <div className="flex justify-end pt-2 border-t border-slate-800">
              <button
                onClick={() => setPreviewDataset(null)}
                className="px-4 py-2 text-xs font-medium rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
