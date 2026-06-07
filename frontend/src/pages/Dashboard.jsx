import React, { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { getDocumentsApi } from "../api/documents";
import { format } from "date-fns";
import toast from "react-hot-toast";

const Dashboard = () => {
  const [documents, setDocuments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("all");

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const data = await getDocumentsApi();
      setDocuments(data);
    } catch (err) {
      toast.error("Failed to load documents catalog");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  // Compute stat card metrics
  const totalCreated = documents.filter((d) => d.status === "draft").length;
  const pendingSignature = documents.filter((d) => d.my_signatory_status === "pending").length;
  const totalCompleted = documents.filter((d) => d.status === "completed").length;
  const totalInSigning = documents.filter((d) => d.status === "in_signing").length;

  const filteredDocuments = documents.filter((doc) => {
    if (activeTab === "my-docs") return doc.status === "draft" || doc.status === "in_signing";
    if (activeTab === "pending") return doc.my_signatory_status === "pending";
    if (activeTab === "completed") return doc.status === "completed";
    return true;
  });

  return (
    <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      <div>
        <h1 class="text-2xl font-extrabold text-slate-900">Document Console</h1>
        <p class="text-sm text-slate-500 font-medium">Create documents, configure sequential signatories, and sign documents.</p>
      </div>

      {/* Stats Cards Section */}
      <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {/* Total Drafts */}
        <div class="bg-white overflow-hidden shadow-sm rounded-lg border border-slate-200 p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0 bg-slate-100 rounded-md p-3">
              <svg class="h-6 w-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-xs font-bold text-slate-400 uppercase tracking-wider">Draft Documents</dt>
                <dd class="text-2xl font-black text-slate-800">{totalCreated}</dd>
              </dl>
            </div>
          </div>
        </div>

        {/* Pending Action */}
        <div class="bg-white overflow-hidden shadow-sm rounded-lg border border-amber-200 p-5 relative">
          <div class="absolute top-0 left-0 right-0 h-1 bg-amber-500" />
          <div class="flex items-center">
            <div class="flex-shrink-0 bg-amber-50 rounded-md p-3">
              <svg class="h-6 w-6 text-amber-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
              </svg>
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-xs font-bold text-slate-400 uppercase tracking-wider">Pending My Signature</dt>
                <dd class="text-2xl font-black text-slate-800">{pendingSignature}</dd>
              </dl>
            </div>
          </div>
        </div>

        {/* Total In Signing */}
        <div class="bg-white overflow-hidden shadow-sm rounded-lg border border-slate-200 p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0 bg-slate-100 rounded-md p-3">
              <svg class="h-6 w-6 text-slate-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-xs font-bold text-slate-400 uppercase tracking-wider">Active Signing flows</dt>
                <dd class="text-2xl font-black text-slate-800">{totalInSigning}</dd>
              </dl>
            </div>
          </div>
        </div>

        {/* Total Completed */}
        <div class="bg-white overflow-hidden shadow-sm rounded-lg border border-green-200 p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0 bg-green-50 rounded-md p-3">
              <svg class="h-6 w-6 text-green-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-xs font-bold text-slate-400 uppercase tracking-wider">Completed Signing</dt>
                <dd class="text-2xl font-black text-slate-800">{totalCompleted}</dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      {/* Tabs Catalog View */}
      <div class="bg-white border border-slate-200 rounded-lg shadow-sm">
        <div class="border-b border-slate-200 px-6 py-4 flex items-center justify-between flex-wrap gap-4">
          <div class="flex space-x-1 bg-slate-100 p-1 rounded-md">
            {[
              { id: "all", label: "All Documents" },
              { id: "my-docs", label: "My Flow/Drafts" },
              { id: "pending", label: "Awaiting Action" },
              { id: "completed", label: "Completed" },
            ].map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                class={`px-4 py-2 rounded text-xs font-semibold uppercase tracking-wider transition-colors ${
                  activeTab === tab.id
                    ? "bg-white text-slate-900 shadow-xs"
                    : "text-slate-500 hover:text-slate-900"
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
          <Link
            to="/documents/new"
            class="inline-flex items-center px-4 py-2 bg-brand-800 hover:bg-brand-700 text-white rounded text-xs font-bold uppercase tracking-wider shadow-sm transition-colors"
          >
            Create New Document
          </Link>
        </div>

        {/* Document list render */}
        {loading ? (
          <div class="flex justify-center items-center py-24">
            <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-brand-800"></div>
          </div>
        ) : filteredDocuments.length === 0 ? (
          <div class="text-center py-24 text-slate-500">
            <svg class="mx-auto h-12 w-12 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-3-3v6m-9 1V4a2 2 0 012-2h6l2 2h6a2 2 0 012 2v10a2 2 0 01-2 2H5a2 2 0 01-2-2z" />
            </svg>
            <p class="mt-4 text-sm font-medium">No documents match the active filter criteria.</p>
          </div>
        ) : (
          <div class="overflow-x-auto">
            <table class="min-w-full divide-y divide-slate-200">
              <thead class="bg-slate-50 text-[10px] font-bold text-slate-500 uppercase tracking-widest text-left">
                <tr>
                  <th class="px-6 py-3">Document Title</th>
                  <th class="px-6 py-3">Subject Line</th>
                  <th class="px-6 py-3">Created By</th>
                  <th class="px-6 py-3">Created Date</th>
                  <th class="px-6 py-3">Signatories</th>
                  <th class="px-6 py-3">Status</th>
                  <th class="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-slate-200 text-sm text-slate-700 font-medium">
                {filteredDocuments.map((doc) => (
                  <tr key={doc.id} class="hover:bg-slate-50">
                    <td class="px-6 py-4 whitespace-nowrap text-slate-900 font-semibold">{doc.title}</td>
                    <td class="px-6 py-4 whitespace-nowrap truncate max-w-xs">{doc.subject}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-xs text-slate-600">{doc.creator_name || "Unknown"}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-xs text-slate-600">
                      {format(new Date(doc.created_at), "dd MMM yyyy")}
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-xs text-slate-600">
                      <span class="inline-flex items-center px-2 py-0.5 rounded-full font-bold bg-slate-100 text-slate-800">
                        {doc.signatory_count} users
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap">
                      <span class={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-bold uppercase tracking-wider ${
                        doc.status === "completed"
                          ? "bg-green-100 text-green-800"
                          : doc.status === "in_signing"
                          ? "bg-amber-100 text-amber-800"
                          : doc.status === "recalled"
                          ? "bg-red-100 text-red-800"
                          : "bg-slate-100 text-slate-800"
                      }`}>
                        {doc.status}
                      </span>
                    </td>
                    <td class="px-6 py-4 whitespace-nowrap text-right text-xs">
                      {doc.my_signatory_status === "pending" ? (
                        <Link
                          to={`/documents/${doc.id}/sign`}
                          class="inline-flex items-center px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white rounded font-bold uppercase tracking-wider"
                        >
                          Sign Document
                        </Link>
                      ) : (
                        <Link
                          to={`/documents/${doc.id}`}
                          class="inline-flex items-center px-3 py-1.5 border border-slate-300 rounded hover:bg-slate-50 text-slate-700 font-bold uppercase tracking-wider"
                        >
                          View Detail
                        </Link>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default Dashboard;
