import React, { useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import toast from "react-hot-toast";

const Login = () => {
  const { login, loginWithMfa } = useAuth();
  const navigate = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  
  // State for handling the multi-step flow
  const [mfaRequired, setMfaRequired] = useState(false);
  const [tempToken, setTempToken] = useState("");
  const [mfaCode, setMfaCode] = useState("");

  const { register, handleSubmit, formState: { errors } } = useForm();

  const onSubmit = async (data) => {
    setSubmitting(true);
    try {
      const result = await login(data.email, data.password);
      
      if (result.mfa_required) {
        setMfaRequired(true);
        setTempToken(result.temp_token);
        toast.success("MFA verification code required");
      } else if (result.needs_mfa_setup) {
        // Redirect to Setup MFA page passing the temp_token
        navigate("/setup-mfa", { state: { tempToken: result.temp_token } });
      } else {
        toast.success("Successfully logged in");
        navigate("/");
      }
    } catch (err) {
      const message = err.response?.data?.detail || "Invalid email or password";
      toast.error(message);
    } finally {
      setSubmitting(false);
    }
  };

  const handleMfaSubmit = async (e) => {
    e.preventDefault();
    if (mfaCode.length !== 6) {
      toast.error("Please enter a valid 6-digit code");
      return;
    }

    setSubmitting(true);
    try {
      await loginWithMfa(tempToken, mfaCode);
      toast.success("Successfully verified");
      navigate("/");
    } catch (err) {
      toast.error(err.response?.data?.detail || "Invalid verification code");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div class="min-h-screen bg-slate-50 flex flex-col justify-center py-12 sm:px-6 lg:px-8">
      <div class="sm:mx-auto sm:w-full sm:max-w-md">
        <h1 class="text-center text-3xl font-extrabold text-brand-800 tracking-tight">DocSign</h1>
        <p class="mt-2 text-center text-sm text-slate-500 font-medium">
          Enterprise Digital Document Signing Platform
        </p>
      </div>

      <div class="mt-8 sm:mx-auto sm:w-full sm:max-w-md">
        <div class="bg-white py-8 px-4 shadow-sm sm:rounded-lg sm:px-10 border border-slate-200">
          {!mfaRequired ? (
            // Step 1: Password authentication form
            <form onSubmit={handleSubmit(onSubmit)} class="space-y-6">
              <div>
                <label htmlFor="email" class="block text-sm font-semibold text-slate-700">
                  Work Email Address
                </label>
                <div class="mt-1">
                  <input
                    id="email"
                    type="email"
                    autoComplete="email"
                    {...register("email", { required: "Email is required" })}
                    class="appearance-none block w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                  />
                  {errors.email && (
                    <p class="mt-1 text-xs text-red-600">{errors.email.message}</p>
                  )}
                </div>
              </div>

              <div>
                <label htmlFor="password" class="block text-sm font-semibold text-slate-700">
                  Password
                </label>
                <div class="mt-1">
                  <input
                    id="password"
                    type="password"
                    autoComplete="current-password"
                    {...register("password", { required: "Password is required" })}
                    class="appearance-none block w-full px-3 py-2 border border-slate-300 rounded-md shadow-sm placeholder-slate-400 focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-sm bg-slate-50"
                  />
                  {errors.password && (
                    <p class="mt-1 text-xs text-red-600">{errors.password.message}</p>
                  )}
                </div>
              </div>

              <div>
                <button
                  type="submit"
                  disabled={submitting}
                  class="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-800 hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-brand-800 disabled:bg-slate-300 transition-colors"
                >
                  {submitting ? "Processing..." : "Sign In"}
                </button>
              </div>
            </form>
          ) : (
            // Step 2: Multi-Factor Authentication input form
            <form onSubmit={handleMfaSubmit} class="space-y-6">
              <div>
                <label htmlFor="mfaCode" class="block text-sm font-semibold text-slate-700 text-center">
                  Enter 6-Digit MFA Verification Code
                </label>
                <p class="text-xs text-slate-500 text-center mt-1">
                  Input the current verification code displayed inside Google Authenticator.
                </p>
                <div class="mt-4 max-w-xs mx-auto">
                  <input
                    id="mfaCode"
                    type="text"
                    maxLength="6"
                    pattern="\d{6}"
                    placeholder="000000"
                    value={mfaCode}
                    onChange={(e) => setMfaCode(e.target.value.replace(/\D/g, ""))}
                    class="block w-full px-4 py-3 text-center text-2xl font-bold tracking-widest border border-slate-300 rounded-md shadow-sm placeholder-slate-300 focus:outline-none focus:ring-brand-800 focus:border-brand-800 bg-slate-50 focus:bg-white"
                  />
                </div>
              </div>

              <div class="flex space-x-3">
                <button
                  type="button"
                  onClick={() => setMfaRequired(false)}
                  class="w-1/3 py-2 px-4 border border-slate-300 rounded-md text-sm font-medium text-slate-700 hover:bg-slate-50 focus:outline-none"
                >
                  Back
                </button>
                <button
                  type="submit"
                  disabled={submitting || mfaCode.length !== 6}
                  class="w-2/3 flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-brand-800 hover:bg-brand-700 focus:outline-none disabled:bg-slate-300"
                >
                  {submitting ? "Verifying..." : "Verify Code"}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
};

export default Login;
