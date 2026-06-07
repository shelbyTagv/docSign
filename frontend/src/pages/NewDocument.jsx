import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { createDocumentApi, setSignatoriesApi, sendDocumentApi } from "../api/documents";
import { searchUsersApi } from "../api/users";
import toast from "react-hot-toast";

const NewDocument = () => {
  const navigate = useNavigate();
  const [step, setStep] = useState(1); // Step 1: metadata, Step 2: add signatories
  const [docId, setDocId] = useState("");
  const [createdDoc, setCreatedDoc] = useState(null);

  // Signatories setup states
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState([]);
  const [selectedSignatories, setSelectedSignatories] = useState([]);

  const { register, handleSubmit, watch, formState: { errors } } = useForm();
  const bodyWatch = watch("body", "");
  const subjectWatch = watch("subject", "");
  const toWatch = watch("to_field", "");

  const onMetadataSubmit = async (data) => {
    try {
      const response = await createDocumentApi(data);
      setDocId(response.id);
      setCreatedDoc({ ...data, id: response.id, created_at: response.created_at });
      toast.success("Document draft created successfully");
      setStep(2);
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to create document draft");
    }
  };

  // Search users dynamically for signatory assignment
  useEffect(() => {
    if (searchQuery.trim().length < 2) {
      setSearchResults([]);
      return;
    }
    const search = async () => {
      try {
        const users = await searchUsersApi(searchQuery);
        setSearchResults(users);
      } catch (err) {
        console.error("User search failed:", err);
      }
    };
    const delayDebounce = setTimeout(search, 300);
    return () => clearTimeout(delayDebounce);
  }, [searchQuery]);

  const addSignatory = (user) => {
    // Avoid double assignment
    if (selectedSignatories.some((s) => s.user_id === user.id)) {
      toast.error("User is already in the signatories list");
      return;
    }

    // Verify signatory has signature registered
    if (!user.identity_verified) {
      toast.error("This user has not registered a signature. Signatories must have a registered signature.");
      return;
    }

    const nextOrder = selectedSignatories.length + 1;
    setSelectedSignatories([
      ...selectedSignatories,
      {
        user_id: user.id,
        full_name: user.full_name,
        email: user.email,
        title: user.title,
        department: user.department,
        order_index: nextOrder,
        is_final_decision_maker: false,
      },
    ]);
    setSearchQuery("");
    setSearchResults([]);
  };

  const removeSignatory = (userId) => {
    const updated = selectedSignatories
      .filter((s) => s.user_id !== userId)
      .map((item, idx) => ({ ...item, order_index: idx + 1 })); // Re-calculate indexes
    setSelectedSignatories(updated);
  };

  const moveSignatory = (index, direction) => {
    const nextList = [...selectedSignatories];
    if (direction === "up" && index > 0) {
      const temp = nextList[index];
      nextList[index] = nextList[index - 1];
      nextList[index - 1] = temp;
    } else if (direction === "down" && index < nextList.length - 1) {
      const temp = nextList[index];
      nextList[index] = nextList[index + 1];
      nextList[index + 1] = temp;
    }

    // Re-evaluate ordering parameters
    const reordered = nextList.map((item, idx) => ({ ...item, order_index: idx + 1 }));
    setSelectedSignatories(reordered);
  };

  const toggleFinalDecision = (userId) => {
    const updated = selectedSignatories.map((s) => {
      if (s.user_id === userId) {
        return { ...s, is_final_decision_maker: !s.is_final_decision_maker };
      }
      return s;
    });
    setSelectedSignatories(updated);
  };

  const handleSendWorkflow = async () => {
    if (selectedSignatories.length === 0) {
      toast.error("Assign at least one signatory to launch workflow");
      return;
    }

    try {
      // Step 1: Submit signatory ordering setup
      const payload = selectedSignatories.map((s) => ({
        user_id: s.user_id,
        order_index: s.order_index,
        is_final_decision_maker: s.is_final_decision_maker,
      }));
      
      await setSignatoriesApi(docId, payload);
      
      // Step 2: Trigger workflow activation and mail delivery
      await sendDocumentApi(docId);
      
      toast.success("Document locked and sent to first signatory");
      navigate("/");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Workflow launch error");
    }
  };

  return (
    <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      <div>
        <h1 class="text-2xl font-extrabold text-slate-900">Create New Document</h1>
        <p class="text-sm text-slate-500 font-medium">Compose document draft, order signatory approvals, and start workflow.</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-2 gap-8 items-start">
        {/* Left Form controls */}
        <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
          {step === 1 ? (
            <form onSubmit={handleSubmit(onMetadataSubmit)} class="space-y-6">
              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">Document Title</label>
                <input
                  type="text"
                  {...register("title", { required: "Title is required" })}
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                  placeholder="e.g. Q3 Sales Budget Approval"
                />
                {errors.title && <p class="mt-1 text-xs text-red-600">{errors.title.message}</p>}
              </div>

              <div class="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">Recipient (To)</label>
                  <input
                    type="text"
                    {...register("to_field", { required: "Recipient name is required" })}
                    class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                    placeholder="e.g. Director of Finance"
                  />
                  {errors.to_field && <p class="mt-1 text-xs text-red-600">{errors.to_field.message}</p>}
                </div>
                <div>
                  <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">CC Partners (Optional)</label>
                  <input
                    type="text"
                    {...register("cc_field")}
                    class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                    placeholder="e.g. Audit Committee"
                  />
                </div>
              </div>

              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">Reference (Ref Number)</label>
                <input
                  type="text"
                  {...register("ref_field")}
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                  placeholder="e.g. DD/2026/089"
                />
              </div>

              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">Subject Line</label>
                <input
                  type="text"
                  {...register("subject", { required: "Subject is required" })}
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                  placeholder="e.g. Allocation of operational budgets for Q3"
                />
                {errors.subject && <p class="mt-1 text-xs text-red-600">{errors.subject.message}</p>}
              </div>

              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">Letter Body Text</label>
                <textarea
                  rows="8"
                  {...register("body", { required: "Document body is required" })}
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50 font-mono"
                  placeholder="Write details of your document..."
                />
                {errors.body && <p class="mt-1 text-xs text-red-600">{errors.body.message}</p>}
              </div>

              <button
                type="submit"
                class="w-full flex justify-center py-2 px-4 border border-transparent rounded shadow-sm text-sm font-semibold text-white bg-brand-800 hover:bg-brand-700"
              >
                Save Draft & Proceed
              </button>
            </form>
          ) : (
            // Step 2: Signatory mapping interface
            <div class="space-y-6">
              <h2 class="text-lg font-bold text-slate-900 border-b border-slate-100 pb-2">Assign Signatories (Sequential Order)</h2>
              
              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider mb-1">Search Staff Users</label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  class="block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                  placeholder="Search by name or work email address..."
                />

                {/* Dropdown containing search queries results */}
                {searchResults.length > 0 && (
                  <ul class="border border-slate-200 mt-1 max-h-48 overflow-y-auto bg-white rounded divide-y divide-slate-100 shadow-md">
                    {searchResults.map((user) => (
                      <li
                        key={user.id}
                        onClick={() => addSignatory(user)}
                        class="px-4 py-2 hover:bg-slate-50 cursor-pointer flex justify-between items-center text-xs"
                      >
                        <div>
                          <p class="font-bold text-slate-800">{user.full_name}</p>
                          <p class="text-slate-500">{user.email} • {user.title || "Staff"}</p>
                        </div>
                        {user.identity_verified ? (
                          <span class="px-2 py-0.5 rounded-full bg-green-100 text-green-800 font-semibold scale-90">Ready</span>
                        ) : (
                          <span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-semibold scale-90">No Signature Profile</span>
                        )}
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              {/* Signatories Sequence display */}
              <div class="space-y-3">
                <h3 class="text-xs font-bold text-slate-500 uppercase tracking-wider">Signing Sequence</h3>
                {selectedSignatories.length === 0 ? (
                  <p class="text-xs text-slate-400 italic">No signatories assigned yet. Search and add above.</p>
                ) : (
                  <div class="space-y-2">
                    {selectedSignatories.map((sig, idx) => (
                      <div key={sig.user_id} class="flex items-center justify-between p-3 border border-slate-200 rounded bg-slate-50">
                        <div class="flex items-center space-x-3">
                          <span class="h-6 w-6 rounded-full bg-brand-800 text-white font-bold text-xs flex items-center justify-center">
                            {sig.order_index}
                          </span>
                          <div>
                            <p class="font-bold text-slate-800 text-xs">{sig.full_name}</p>
                            <p class="text-slate-500 text-[10px]">{sig.title || "Officer"} • {sig.department}</p>
                          </div>
                        </div>

                        <div class="flex items-center space-x-2">
                          <button
                            type="button"
                            onClick={() => toggleFinalDecision(sig.user_id)}
                            class={`px-2 py-1 rounded text-[10px] font-bold tracking-wider uppercase border transition-colors ${
                              sig.is_final_decision_maker
                                ? "bg-red-50 border-red-200 text-red-700"
                                : "bg-white border-slate-200 text-slate-500 hover:bg-slate-100"
                            }`}
                          >
                            {sig.is_final_decision_maker ? "Decision Maker" : "Recommend Only"}
                          </button>
                          
                          <button
                            onClick={() => moveSignatory(idx, "up")}
                            disabled={idx === 0}
                            class="text-slate-400 hover:text-slate-600 disabled:opacity-30"
                          >
                            ▲
                          </button>
                          <button
                            onClick={() => moveSignatory(idx, "down")}
                            disabled={idx === selectedSignatories.length - 1}
                            class="text-slate-400 hover:text-slate-600 disabled:opacity-30"
                          >
                            ▼
                          </button>
                          <button
                            onClick={() => removeSignatory(sig.user_id)}
                            class="text-red-500 hover:text-red-700 ml-2 text-xs font-bold"
                          >
                            Remove
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              <div class="flex space-x-3 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setStep(1)}
                  class="w-1/3 py-2 border border-slate-300 rounded text-sm text-slate-600 hover:bg-slate-50 font-bold uppercase tracking-wider"
                >
                  Edit Document
                </button>
                <button
                  type="button"
                  onClick={handleSendWorkflow}
                  disabled={selectedSignatories.length === 0}
                  class="w-2/3 py-2 bg-brand-800 hover:bg-brand-700 text-white rounded text-sm font-bold uppercase tracking-wider disabled:bg-slate-300 transition-colors shadow-sm"
                >
                  Send for signing
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right Preview container */}
        <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm sticky top-20">
          <h3 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-4">Live Preview</h3>
          <div class="border border-slate-100 rounded-lg shadow-inner bg-slate-50/50 p-4 max-h-[600px] overflow-y-auto">
            {step === 1 ? (
              <div class="font-serif leading-relaxed text-slate-800 text-sm">
                <div class="text-center pb-3 border-b-2 border-slate-200 mb-6 font-sans">
                  <h4 class="font-black text-brand-800 uppercase text-base tracking-wider">My Organization</h4>
                  <p class="text-[10px] text-slate-400 mt-1 uppercase tracking-widest">Digital Document Management System</p>
                </div>
                
                <div class="space-y-1 text-xs font-sans mb-6">
                  <p><span class="font-bold text-slate-400 mr-2">TO:</span> {toWatch || "[To Field]"}</p>
                  <p><span class="font-bold text-slate-400 mr-2">SUBJECT:</span> {subjectWatch || "[Subject]"}</p>
                </div>
                
                <div class="whitespace-pre-wrap min-h-[150px]">
                  {bodyWatch || "Document body preview..."}
                </div>
              </div>
            ) : (
              createdDoc && (
                <div class="font-serif leading-relaxed text-slate-800 text-sm">
                  <div class="text-center pb-3 border-b-2 border-slate-200 mb-6 font-sans">
                    <h4 class="font-black text-brand-800 uppercase text-base tracking-wider">My Organization</h4>
                    <p class="text-[10px] text-slate-400 mt-1 uppercase tracking-widest">Digital Document Management System</p>
                  </div>
                  
                  <div class="space-y-1 text-xs font-sans mb-6">
                    <p><span class="font-bold text-slate-400 mr-2">TO:</span> {createdDoc.to_field}</p>
                    <p><span class="font-bold text-slate-400 mr-2">SUBJECT:</span> {createdDoc.subject}</p>
                  </div>
                  
                  <div class="whitespace-pre-wrap mb-10">
                    {createdDoc.body}
                  </div>

                  {/* Signatories ordering block lists preview */}
                  <div class="font-sans border-t border-slate-200 pt-4 mt-6">
                    <h5 class="text-xs font-bold text-slate-400 uppercase tracking-wider mb-2">Pending Workflow Signatories</h5>
                    <div class="space-y-1">
                      {selectedSignatories.map((s) => (
                        <p key={s.user_id} class="text-[10px] text-slate-500">
                          {s.order_index}. {s.full_name} ({s.title || "Officer"})
                        </p>
                      ))}
                    </div>
                  </div>
                </div>
              )
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default NewDocument;
