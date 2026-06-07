import React from "react";
import { format } from "date-fns";

const DocumentViewer = ({ document }) => {
  if (!document) return null;

  const formatDate = (isoString) => {
    if (!isoString) return "";
    try {
      // Formats the timestamp to clean display string
      return format(new Date(isoString), "dd MMMM yyyy 'at' HH:mm");
    } catch (e) {
      return isoString;
    }
  };

  return (
    <div class="bg-white border border-slate-200 shadow-sm rounded-lg max-w-4xl mx-auto p-8 sm:p-12 font-serif text-slate-900 leading-relaxed relative overflow-hidden">
      {/* Decorative corporate top bar */}
      <div class="absolute top-0 left-0 right-0 h-1.5 bg-brand-800" />
      
      {/* Letterhead */}
      <div class="text-center font-sans border-b-2 border-brand-800 pb-4 mb-8">
        <h1 class="text-2xl font-bold tracking-wider text-brand-800 uppercase">My Organization</h1>
        <p class="text-xs text-slate-500 tracking-widest mt-1 uppercase">Digital Document Management System</p>
      </div>

      {/* Meta block */}
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 text-sm font-sans mb-8 border-b border-slate-100 pb-6">
        <div class="space-y-2">
          {document.ref_field && (
            <p>
              <span class="font-semibold text-slate-500 mr-2 uppercase">Ref:</span>
              <span class="font-mono text-slate-800">{document.ref_field}</span>
            </p>
          )}
          <p>
            <span class="font-semibold text-slate-500 mr-2 uppercase">Date:</span>
            <span class="text-slate-800">{formatDate(document.created_at)}</span>
          </p>
          <p>
            <span class="font-semibold text-slate-500 mr-2 uppercase">Creator:</span>
            <span class="text-slate-800">{document.creator_name || "Unknown Creator"}</span>
          </p>
        </div>
        <div class="space-y-2">
          <p>
            <span class="font-semibold text-slate-500 mr-2 uppercase">To:</span>
            <span class="text-slate-800 font-medium">{document.to_field}</span>
          </p>
          {document.cc_field && (
            <p>
              <span class="font-semibold text-slate-500 mr-2 uppercase">CC:</span>
              <span class="text-slate-800">{document.cc_field}</span>
            </p>
          )}
          <p>
            <span class="font-semibold text-slate-500 mr-2 uppercase">Status:</span>
            <span class={`inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold uppercase ${
              document.status === "completed"
                ? "bg-green-100 text-green-800"
                : document.status === "in_signing"
                ? "bg-amber-100 text-amber-800"
                : document.status === "recalled"
                ? "bg-red-100 text-red-800"
                : "bg-slate-100 text-slate-800"
            }`}>
              {document.status}
            </span>
          </p>
        </div>
      </div>

      {/* Subject Line */}
      <div class="mb-8 font-sans">
        <h2 class="text-lg font-bold text-slate-900 border-b-2 border-slate-200 pb-2">
          SUBJECT: {document.subject}
        </h2>
      </div>

      {/* Body content */}
      <div class="whitespace-pre-wrap text-base font-serif text-slate-800 mb-12 min-h-[250px]">
        {document.body}
      </div>

      {/* Signatures block display */}
      {document.signatures && document.signatures.length > 0 && (
        <div class="mt-12 pt-8 border-t border-slate-200 font-sans">
          <h3 class="text-sm font-semibold uppercase tracking-wider text-slate-500 mb-6">Digital Signatures</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
            {document.signatures.map((sig) => {
              const signatory = document.signatories?.find(s => s.user_id === sig.user_id);
              return (
                <div key={sig.id} class="bg-slate-50 p-4 rounded border border-slate-200 flex flex-col justify-between">
                  <div class="border-b border-slate-200 pb-3 mb-3">
                    {sig.signature_image_base64 ? (
                      <img
                        src={`data:image/png;base64,${sig.signature_image_base64}`}
                        alt="Applied signature"
                        class="max-h-16 max-w-full mx-auto mix-blend-multiply"
                      />
                    ) : (
                      <div class="h-16 flex items-center justify-center text-xs text-slate-400 font-mono italic">
                        [Biometric Stamp Encrypted]
                      </div>
                    )}
                  </div>

                  <div>
                    <p class="font-bold text-sm text-slate-800">{sig.user_full_name || "Signatory"}</p>
                    <p class="text-xs text-slate-500">{signatory?.user_title || "Officer"}</p>
                    <p class="text-[10px] text-slate-400 mt-2 font-mono">
                      Timestamp: {formatDate(sig.signed_at)}
                    </p>
                    <p class="text-[10px] text-slate-400 font-mono">
                      IP Address: {sig.ip_address}
                    </p>
                    
                    {sig.recommendation !== "none" && (
                      <div class="mt-3 text-xs flex items-center space-x-1.5">
                        <span class={`font-bold ${sig.recommendation === 'recommended' ? 'text-green-700' : 'text-red-700'}`}>
                          {sig.recommendation === 'recommended' ? '✓ Recommended' : '✗ Not Recommended'}
                        </span>
                      </div>
                    )}
                    {sig.note && (
                      <p class="mt-2 text-xs italic text-slate-600 bg-white p-2 rounded border border-slate-100">
                        "{sig.note}"
                      </p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};

export default DocumentViewer;
