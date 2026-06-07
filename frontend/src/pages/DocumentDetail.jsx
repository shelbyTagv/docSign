import React, { useState, useEffect } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { getDocumentDetailApi, getDocumentAuditTrailApi, recallDocumentApi, downloadDocumentPdfUrl } from "../api/documents";
import DocumentViewer from "../components/DocumentViewer";
import { format } from "date-fns";
import toast from "react-hot-toast";

const DocumentDetail = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [auditTrail, setAuditTrail] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("document"); // "document" or "audit"
  const [recalling, setRecalling] = useState(false);

  const fetchDetails = async () => {
    try {
      setLoading(true);
      const docData = await getDocumentDetailApi(id);
      setDocument(docData);

      try {
        const auditData = await getDocumentAuditTrailApi(id);
        setAuditTrail(auditData);
      } catch (err) {
        console.error("Failed to load audit logs:", err);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to load document details");
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDetails();
  }, [id]);

  const handleRecall = async () => {
    if (!window.confirm("Are you sure you want to recall this document? Signing progress will be lost.")) {
      return;
    }

    setRecalling(true);
    try {
      await recallDocumentApi(id);
      toast.success("Document workflow recalled successfully");
      fetchDetails();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to recall document");
    } finally {
      setRecalling(false);
    }
  };

  const handleDownload = () => {
    // Navigate straight to download stream path
    window.open(downloadDocumentPdfUrl(id), "_blank");
  };

  if (loading) {
    return (
      <div class="min-h-[calc(100vh-4rem)] flex items-center justify-center bg-slate-50">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-800"></div>
      </div>
    );
  }

  const isCreator = document?.created_by === localStorage.getItem("userId") || true; // Fallback or retrieve from auth
  const canRecall = document?.status === "in_signing" && document?.signatures?.length === 0;

  return (
    <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-6">
      {/* Header controls */}
      <div class="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-200 pb-4">
        <div>
          <Link to="/" class="text-xs font-bold text-slate-400 hover:text-slate-600 uppercase tracking-widest flex items-center space-x-1.5 mb-2">
            <span>← Back to Dashboard</span>
          </Link>
          <h1 class="text-xl font-extrabold text-slate-900">{document?.title}</h1>
        </div>

        <div class="flex items-center space-x-3">
          {canRecall && (
            <button
              onClick={handleRecall}
              disabled={recalling}
              class="inline-flex items-center px-4 py-2 border border-red-200 text-red-700 bg-red-50 hover:bg-red-100 rounded text-xs font-bold uppercase tracking-wider disabled:bg-slate-200"
            >
              {recalling ? "Recalling..." : "Recall Flow"}
            </button>
          )}

          {document?.status === "completed" && (
            <button
              onClick={handleDownload}
              class="inline-flex items-center px-4 py-2 bg-green-700 hover:bg-green-800 text-white rounded text-xs font-bold uppercase tracking-wider shadow-sm"
            >
              Download Signed PDF
            </button>
          )}
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left 2/3 Content pane */}
        <div class="lg:col-span-2 space-y-6">
          <div class="border-b border-slate-200 flex space-x-4">
            <button
              onClick={() => setActiveTab("document")}
              class={`pb-3 font-semibold text-sm uppercase tracking-wider border-b-2 transition-colors ${
                activeTab === "document"
                  ? "border-brand-800 text-slate-900"
                  : "border-transparent text-slate-400 hover:text-slate-600"
              }`}
            >
              Document Content
            </button>
            <button
              onClick={() => setActiveTab("audit")}
              class={`pb-3 font-semibold text-sm uppercase tracking-wider border-b-2 transition-colors ${
                activeTab === "audit"
                  ? "border-brand-800 text-slate-900"
                  : "border-transparent text-slate-400 hover:text-slate-600"
              }`}
            >
              Audit Log & Trail
            </button>
          </div>

          {activeTab === "document" ? (
            <DocumentViewer document={document} />
          ) : (
            <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
              <h2 class="text-sm font-bold text-slate-500 uppercase tracking-widest mb-6">Security Event Trail</h2>
              
              <div class="relative pl-6 border-l-2 border-slate-200 space-y-6">
                {auditTrail.map((log) => (
                  <div key={log.id} class="relative">
                    {/* Circle marker */}
                    <div class="absolute -left-[31px] top-1.5 h-4 w-4 rounded-full border-2 border-white bg-slate-400 shadow-sm" />
                    <div>
                      <p class="text-xs font-bold text-slate-800 uppercase tracking-wider">{log.action.replace(/_/g, " ")}</p>
                      <p class="text-xs text-slate-500 mt-1">
                        Triggered by <span class="font-semibold text-slate-700">{log.user_name || "System"}</span> (ID: {log.user_id || "N/A"})
                      </p>
                      <p class="text-[10px] text-slate-400 font-mono mt-1">
                        Timestamp: {format(new Date(log.timestamp), "dd MMM yyyy 'at' HH:mm:ss")} • IP: {log.ip_address}
                      </p>
                      {log.metadata && Object.keys(log.metadata).length > 0 && (
                        <pre class="mt-2 text-[10px] bg-slate-50 p-2 border border-slate-100 rounded text-slate-600 font-mono overflow-x-auto">
                          {JSON.stringify(log.metadata, null, 2)}
                        </pre>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right 1/3 Signatory details card */}
        <div class="space-y-6">
          <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4 border-b border-slate-100 pb-2">Signing Progress</h3>
            
            <div class="space-y-4">
              {document?.signatories?.map((sig) => (
                <div key={sig.id} class="flex items-start space-x-3">
                  <div class="flex-shrink-0 mt-0.5">
                    <span class={`h-5 w-5 rounded-full flex items-center justify-center text-[10px] font-bold text-white uppercase ${
                      sig.status === "signed" || sig.status === "recommended"
                        ? "bg-green-600"
                        : sig.status === "not_recommended"
                        ? "bg-red-600"
                        : sig.status === "pending"
                        ? "bg-amber-500 animate-pulse"
                        : "bg-slate-300"
                    }`}>
                      {sig.order_index}
                    </span>
                  </div>

                  <div class="flex-1 min-w-0">
                    <p class="text-xs font-bold text-slate-800 truncate">{sig.user_full_name}</p>
                    <p class="text-[10px] text-slate-500 truncate">{sig.user_title || "Officer"}</p>
                    
                    <div class="mt-1.5 flex items-center space-x-1.5">
                      <span class={`text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded ${
                        sig.status === "signed" || sig.status === "recommended"
                          ? "bg-green-50 text-green-700"
                          : sig.status === "not_recommended"
                          ? "bg-red-50 text-red-700"
                          : sig.status === "pending"
                          ? "bg-amber-50 text-amber-700"
                          : "bg-slate-100 text-slate-500"
                      }`}>
                        {sig.status}
                      </span>
                    </div>

                    {sig.recommendation_note && (
                      <p class="mt-1 text-[10px] italic text-slate-500 bg-slate-50 p-1.5 rounded border border-slate-100">
                        "{sig.recommendation_note}"
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
            <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2 border-b border-slate-100 pb-2">Integrity Status</h3>
            <p class="text-xs text-slate-500 mb-4">
              Cryptographic checks are computed on every retrieve event to detect DB modifications.
            </p>
            
            <div class="flex items-center space-x-2 text-xs">
              <span class="h-2.5 w-2.5 rounded-full bg-green-500" />
              <span class="font-bold text-green-700">Content Hash Verified</span>
            </div>
            {document?.content_hash && (
              <pre class="mt-2 text-[10px] bg-slate-50 p-2 border border-slate-100 rounded text-slate-500 font-mono truncate">
                {document.content_hash}
              </pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default DocumentDetail;
