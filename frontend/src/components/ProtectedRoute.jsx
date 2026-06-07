import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ProtectedRoute = ({ requiredPermission }) => {
  const { user, loading, hasPermission } = useAuth();

  if (loading) {
    return (
      <div class="flex items-center justify-center min-h-screen bg-slate-50">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-800"></div>
      </div>
    );
  }

  if (!user) {
    // Save previous path to redirect user after successful login
    return <Navigate to="/login" replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <div class="min-h-screen flex items-center justify-center bg-slate-50 px-4">
        <div class="max-w-md w-full text-center bg-white p-8 rounded-lg shadow-sm border border-slate-200">
          <svg class="mx-auto h-12 w-12 text-red-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          <h2 class="mt-4 text-lg font-semibold text-slate-900">Access Denied</h2>
          <p class="mt-2 text-sm text-slate-600">You do not have the required permissions ({requiredPermission}) to view this resource.</p>
          <div class="mt-6">
            <a href="/" class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-brand-800 hover:bg-brand-700 focus:outline-none">
              Return to Dashboard
            </a>
          </div>
        </div>
      </div>
    );
  }

  return <Outlet />;
};

export default ProtectedRoute;
