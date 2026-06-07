import React, { useState, useEffect } from "react";
import { useAuth } from "../context/AuthContext";
import { getSignaturePreviewApi, uploadSignatureApi, updateMeApi, changePasswordApi } from "../api/users";
import SignatureCanvas from "../components/SignatureCanvas";
import MFAPrompt from "../components/MFAPrompt";
import toast from "react-hot-toast";

const Profile = () => {
  const { user, refreshUser } = useAuth();
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [title, setTitle] = useState(user?.title || "");
  const [department, setDepartment] = useState(user?.department || "");
  const [signaturePreview, setSignaturePreview] = useState("");
  const [isMfaOpen, setIsMfaOpen] = useState(false);
  const [pendingSignature, setPendingSignature] = useState("");
  const [updatingProfile, setUpdatingProfile] = useState(false);

  // Password change states
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [changingPassword, setChangingPassword] = useState(false);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || "");
      setTitle(user.title || "");
      setDepartment(user.department || "");
    }
  }, [user]);

  // Load user signature preview on component mount
  useEffect(() => {
    const fetchSignaturePreview = async () => {
      try {
        const data = await getSignaturePreviewApi();
        setSignaturePreview(data.signature_base64);
      } catch (err) {
        // Safe to ignore if user has not yet drawn/registered any signature
      }
    };
    fetchSignaturePreview();
  }, []);

  const handleUpdateProfile = async (e) => {
    e.preventDefault();
    setUpdatingProfile(true);
    try {
      await updateMeApi({ full_name: fullName, title, department });
      await refreshUser();
      toast.success("Profile information updated");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Profile update failed");
    } finally {
      setUpdatingProfile(false);
    }
  };

  const handleSignatureSave = (base64Data) => {
    setPendingSignature(base64Data);
    setIsMfaOpen(true); // Always verify identity via MFA prompt before saving new signature
  };

  const handleMfaSuccess = async (mfaToken) => {
    try {
      await uploadSignatureApi(pendingSignature, mfaToken);
      toast.success("Signature biometric stamp registered successfully");
      
      // Update signature display in UI
      if (pendingSignature.includes(",")) {
        setSignaturePreview(pendingSignature.split(",")[1]);
      } else {
        setSignaturePreview(pendingSignature);
      }
      
      await refreshUser();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Failed to register signature");
    }
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    if (!currentPassword || !newPassword) {
      toast.error("Please fill in both password fields");
      return;
    }

    setChangingPassword(true);
    try {
      await changePasswordApi({ current_password: currentPassword, new_password: newPassword });
      toast.success("Password changed successfully");
      setCurrentPassword("");
      setNewPassword("");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Password change failed");
    } finally {
      setChangingPassword(false);
    }
  };

  return (
    <div class="max-w-4xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      <div class="flex items-center justify-between border-b border-slate-200 pb-4">
        <div>
          <h1 class="text-2xl font-extrabold text-slate-900">My Profile</h1>
          <p class="text-sm text-slate-500 font-medium">Manage user profile settings and signature records.</p>
        </div>
        <div>
          {user?.identity_verified ? (
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-green-100 text-green-800 border border-green-200 shadow-sm">
              ✓ Identity Verified
            </span>
          ) : (
            <span class="inline-flex items-center px-3 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800 border border-amber-200 animate-pulse">
              ⚠ Verification Pending
            </span>
          )}
        </div>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
        {/* Left Side: Profile & Password settings */}
        <div class="space-y-8">
          <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-950 mb-4 border-b border-slate-100 pb-2">Profile Details</h2>
            <form onSubmit={handleUpdateProfile} class="space-y-4">
              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">Full Name</label>
                <input
                  type="text"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                  required
                />
              </div>

              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">Title / Job Designation</label>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                  placeholder="e.g. Head of Finance"
                />
              </div>

              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">Department</label>
                <input
                  type="text"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                />
              </div>

              <button
                type="submit"
                disabled={updatingProfile}
                class="w-full flex justify-center py-2 px-4 border border-transparent rounded shadow-sm text-sm font-semibold text-white bg-brand-800 hover:bg-brand-700 focus:outline-none disabled:bg-slate-300"
              >
                {updatingProfile ? "Updating..." : "Save Profile"}
              </button>
            </form>
          </div>

          <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
            <h2 class="text-lg font-bold text-slate-950 mb-4 border-b border-slate-100 pb-2">Change Password</h2>
            <form onSubmit={handleChangePassword} class="space-y-4">
              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">Current Password</label>
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                />
              </div>

              <div>
                <label class="block text-xs font-bold text-slate-500 uppercase tracking-wider">New Password</label>
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                />
              </div>

              <button
                type="submit"
                disabled={changingPassword}
                class="w-full flex justify-center py-2 px-4 border border-transparent rounded shadow-sm text-sm font-semibold text-white bg-brand-800 hover:bg-brand-700 focus:outline-none disabled:bg-slate-300"
              >
                {changingPassword ? "Updating Password..." : "Change Password"}
              </button>
            </form>
          </div>
        </div>

        {/* Right Side: Signature Canvas Setup */}
        <div class="space-y-8">
          <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm flex flex-col justify-between">
            <div>
              <h2 class="text-lg font-bold text-slate-950 mb-2 border-b border-slate-100 pb-2">Registered Signature Stamp</h2>
              <p class="text-xs text-slate-500 mb-4">
                This signature will be stamped on locked documents when signing approvals are submitted.
              </p>
              
              <div class="border border-slate-200 rounded bg-slate-50 flex items-center justify-center p-4 min-h-[140px] relative">
                {signaturePreview ? (
                  <img
                    src={`data:image/png;base64,${signaturePreview}`}
                    alt="Registered Signature Preview"
                    class="max-h-24 max-w-full mix-blend-multiply"
                  />
                ) : (
                  <div class="text-slate-400 text-sm font-medium">No signature registered yet</div>
                )}
              </div>
            </div>

            <div class="mt-6">
              <h3 class="text-sm font-bold text-slate-800 mb-3">Register or Update Signature</h3>
              <SignatureCanvas onSave={handleSignatureSave} />
            </div>
          </div>
        </div>
      </div>

      <MFAPrompt
        isOpen={isMfaOpen}
        onClose={() => setIsMfaOpen(false)}
        onSuccess={handleMfaSuccess}
        title="Confirm Signature Stamp Update"
      />
    </div>
  );
};

export default Profile;
