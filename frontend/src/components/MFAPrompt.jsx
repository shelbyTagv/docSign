import React, { useState, useEffect, useRef } from "react";
import { Dialog } from "@headlessui/react";
import { verifyMfaStandaloneApi } from "../api/auth";

const MFAPrompt = ({ isOpen, onClose, onSuccess, title = "MFA Verification Required" }) => {
  const [code, setCode] = useState(new Array(6).fill(""));
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [timer, setTimer] = useState(30);
  const inputsRef = useRef([]);

  // Auto-focus first input on dialog open
  useEffect(() => {
    if (isOpen) {
      setCode(new Array(6).fill(""));
      setError("");
      setTimer(30);
      setTimeout(() => {
        inputsRef.current[0]?.focus();
      }, 150);
    }
  }, [isOpen]);

  // TOTP interval count down helper
  useEffect(() => {
    if (!isOpen) return;
    const interval = setInterval(() => {
      setTimer((prev) => (prev > 1 ? prev - 1 : 30));
    }, 1000);
    return () => clearInterval(interval);
  }, [isOpen]);

  const handleChange = (element, index) => {
    const value = element.value.replace(/[^0-9]/g, "");
    if (!value) return;

    const newCode = [...code];
    newCode[index] = value.substring(value.length - 1);
    setCode(newCode);

    // Auto-advance cursor to the next input box
    if (index < 5 && newCode[index]) {
      inputsRef.current[index + 1].focus();
    }
  };

  const handleKeyDown = (e, index) => {
    if (e.key === "Backspace") {
      const newCode = [...code];
      newCode[index] = "";
      setCode(newCode);

      // Auto-retreat cursor on backspace
      if (index > 0) {
        inputsRef.current[index - 1].focus();
      }
    }
  };

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    const fullCode = code.join("");
    if (fullCode.length !== 6) {
      setError("Please enter all 6 digits");
      return;
    }

    setSubmitting(true);
    setError("");

    try {
      // Validate standalone code and retrieve short-lived session token (mfa_token)
      const data = await verifyMfaStandaloneApi(fullCode);
      if (data.mfa_token) {
        onSuccess(data.mfa_token);
        onClose();
      } else {
        setError("Invalid verification code");
      }
    } catch (err) {
      setError(err.response?.data?.detail || "MFA validation failed. Try again.");
    } finally {
      setSubmitting(false);
    }
  };

  // Trigger submission automatically when all 6 digits are populated
  useEffect(() => {
    if (code.every(val => val !== "") && isOpen) {
      handleSubmit();
    }
  }, [code]);

  return (
    <Dialog open={isOpen} onClose={onClose} class="relative z-50">
      <div class="fixed inset-0 bg-slate-900/60 backdrop-blur-sm" aria-hidden="true" />

      <div class="fixed inset-0 flex items-center justify-center p-4">
        <Dialog.Panel class="mx-auto max-w-md w-full bg-white rounded-lg p-6 shadow-xl border border-slate-200">
          <Dialog.Title class="text-lg font-bold text-slate-900 flex items-center justify-between">
            <span>{title}</span>
            <button onClick={onClose} class="text-slate-400 hover:text-slate-600 focus:outline-none">
              <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </Dialog.Title>

          <Dialog.Description class="mt-2 text-sm text-slate-500">
            Open the Google Authenticator app on your device to fetch your current 6-digit confirmation code.
          </Dialog.Description>

          <form onSubmit={handleSubmit} class="mt-6 space-y-4">
            <div class="flex justify-between max-w-xs mx-auto">
              {code.map((num, idx) => (
                <input
                  key={idx}
                  ref={(el) => (inputsRef.current[idx] = el)}
                  type="text"
                  maxLength="1"
                  value={num}
                  onChange={(e) => handleChange(e.target, idx)}
                  onKeyDown={(e) => handleKeyDown(e, idx)}
                  class="w-12 h-12 text-center text-xl font-bold border border-slate-300 rounded focus:border-brand-800 focus:ring-1 focus:ring-brand-800 bg-slate-50 focus:outline-none"
                  disabled={submitting}
                />
              ))}
            </div>

            {error && (
              <p class="text-center text-xs text-red-600 bg-red-50 py-2 rounded font-medium">{error}</p>
            )}

            <div class="flex items-center justify-between text-xs text-slate-500 mt-2 px-2">
              <span class="flex items-center space-x-1">
                <span class={`h-2.5 w-2.5 rounded-full inline-block ${timer > 10 ? 'bg-green-500' : 'bg-amber-500 animate-ping'}`} />
                <span>Code updates in {timer}s</span>
              </span>
              <span>Expires in 3 minutes</span>
            </div>

            <div class="mt-6 flex justify-end space-x-3">
              <button
                type="button"
                onClick={onClose}
                class="px-4 py-2 border border-slate-300 rounded text-slate-700 hover:bg-slate-50 text-sm font-medium focus:outline-none"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submitting}
                class="px-4 py-2 bg-brand-800 hover:bg-brand-700 text-white rounded text-sm font-medium shadow-sm focus:outline-none disabled:bg-slate-300"
              >
                {submitting ? "Verifying..." : "Verify MFA"}
              </button>
            </div>
          </form>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
};

export default MFAPrompt;
