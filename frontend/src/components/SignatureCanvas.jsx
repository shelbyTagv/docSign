import React, { useRef, useState } from "react";
import SignaturePad from "react-signature-canvas";

const SignatureCanvas = ({ onSave, onClear }) => {
  const padRef = useRef(null);
  const [isEmpty, setIsEmpty] = useState(true);

  const handleClear = () => {
    padRef.current.clear();
    setIsEmpty(true);
    if (onClear) onClear();
  };

  const handleStroke = () => {
    setIsEmpty(padRef.current.isEmpty());
  };

  const handleSave = () => {
    if (padRef.current.isEmpty()) {
      return;
    }
    
    // Export base64 PNG image from the drawn canvas
    const base64Data = padRef.current.getTrimmedCanvas().toDataURL("image/png");
    onSave(base64Data);
  };

  return (
    <div class="bg-white border border-slate-200 rounded-lg p-4 shadow-sm max-w-lg w-full mx-auto">
      <div class="border border-dashed border-slate-300 rounded bg-slate-50 flex items-center justify-center relative h-48 overflow-hidden">
        <SignaturePad
          ref={padRef}
          canvasProps={{
            className: "signature-canvas w-full h-full cursor-crosshair",
          }}
          onEnd={handleStroke}
        />
        {isEmpty && (
          <div class="absolute inset-0 flex items-center justify-center pointer-events-none select-none text-slate-400 text-sm">
            Draw your signature here
          </div>
        )}
      </div>
      
      <div class="mt-4 flex items-center justify-between">
        <button
          type="button"
          onClick={handleClear}
          class="px-4 py-2 border border-slate-300 rounded text-slate-700 hover:bg-slate-50 text-sm font-medium transition-colors"
        >
          Clear Canvas
        </button>

        <button
          type="button"
          disabled={isEmpty}
          onClick={handleSave}
          class={`px-4 py-2 rounded text-white font-medium text-sm shadow-sm transition-all ${
            isEmpty
              ? "bg-slate-300 cursor-not-allowed"
              : "bg-brand-800 hover:bg-brand-700"
          }`}
        >
          Confirm Signature
        </button>
      </div>
    </div>
  );
};

export default SignatureCanvas;
