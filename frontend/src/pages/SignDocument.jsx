import React, { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { getDocumentDetailApi, signDocumentApi } from "../api/documents";
import DocumentViewer from "../components/DocumentViewer";
import MFAPrompt from "../components/MFAPrompt";
import toast from "react-hot-toast";

const SignDocument = () => {
  const { id } = useParams();
  const navigate = useNavigate();
  const [document, setDocument] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isMfaOpen, setIsMfaOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // Sign forms inputs
  const [recommendation, setRecommendation] = useState("none"); // "none", "recommended", "not_recommended"
  const [note, setNote] = useState("");

  const fetchDocument = async () => {
    try {
      setLoading(true);
      const data = await getDocumentDetailApi(id);
      setDocument(data);
    } catch (err) {
      toast.error("Failed to load document");
      navigate("/");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocument();
  }, [id]);

  const handleSignClick = (e) => {
    e.preventDefault();
    setIsMfaOpen(true); // Launch MFA code verification prior to pushing database edits
  };

  const handleMfaSuccess = async (mfaToken) => {
    setSubmitting(true);
    try {
      await signDocumentApi(id, { recommendation, note }, mfaToken);
      toast.success("Document signed successfully");
      navigate(`/documents/${id}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to submit signature");
    } finally {
      setSubmitting(false);
      setIsMfaOpen(false);
    }
  };

  if (loading) {
    return (
      <div class="min-h-screen flex items-center justify-center bg-slate-50">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-800"></div>
      </div>
    );
  }

  return (
    <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      <div class="flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <h1 class="text-xl font-extrabold text-slate-900">Sign Document Approval</h1>
          <p class="text-xs text-slate-500 font-medium mt-1">Review the legal text details and apply your digital signature stamp.</p>
        </div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Document content column */}
        <div class="lg:col-span-2">
          <DocumentViewer document={document} />
        </div>

        {/* Action console column */}
        <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm sticky top-20 space-y-6">
          <h2 class="text-sm font-bold text-slate-500 uppercase tracking-widest border-b border-slate-100 pb-2">Signing Panel</h2>
          
          <form onSubmit={handleSignClick} class="space-y-6">
            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Recommendation Recommendation Option</label>
              <div class="grid grid-cols-3 gap-2">
                {[
                  { id: "none", label: "Sign Only" },
                  { id: "recommended", label: "Recommend" },
                  { id: "not_recommended", label: "Not Recommend" },
                ].map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => setRecommendation(opt.id)}
                    class={`py-2 px-1 text-center rounded text-[10px] font-bold uppercase border transition-colors ${
                      recommendation === opt.id
                        ? "bg-brand-800 border-brand-800 text-white shadow-xs"
                        : "bg-slate-50 border-slate-200 text-slate-600 hover:bg-slate-100"
                    }`}
                  >
                    {opt.label}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Signing Note / Comments (Optional)</label>
              <textarea
                rows="4"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                class="block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-xs bg-slate-50 font-sans"
                placeholder="Include brief feedback or remarks regarding your decision..."
              />
            </div>

            <div class="bg-amber-50 border border-amber-200 rounded p-4 text-[11px] text-amber-800 space-y-2">
              <p class="font-bold">⚠ Cryptographic Disclaimer</p>
              <p>
                By applying your digital signature, you verify that you have read and approved the content of this document.
                This action is logged in an immutable database audit log.
              </p>
            </div>

            <button
              type="submit"
              disabled={submitting}
              class="w-full py-2.5 bg-brand-800 hover:bg-brand-700 text-white rounded font-bold uppercase tracking-wider shadow-sm text-xs"
            >
              Apply Signature
            </button>
          </form>
        </div>
      </div>

      <MFAPrompt
        isOpen={isMfaOpen}
        onClose={() => setIsMfaOpen(false)}
        onSuccess={handleMfaSuccess}
        title="Verify MFA Code to Sign"
      />
    </div>
  );
};

export default SignDocument;
