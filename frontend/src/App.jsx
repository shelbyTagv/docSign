import React from "react";
import { BrowserRouter, Routes, Route, Outlet } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";
import Navbar from "./components/Navbar";
import Sidebar from "./components/Sidebar";

// Pages
import Login from "./pages/Login";
import SetupMFA from "./pages/SetupMFA";
import Dashboard from "./pages/Dashboard";
import NewDocument from "./pages/NewDocument";
import DocumentDetail from "./pages/DocumentDetail";
import SignDocument from "./pages/SignDocument";
import Profile from "./pages/Profile";
import AdminPanel from "./pages/AdminPanel";

import { Toaster } from "react-hot-toast";

// Layout wrapper for authenticated users
const AuthenticatedLayout = () => {
  return (
    <div class="min-h-screen bg-slate-50 flex flex-col">
      <Navbar />
      <div class="flex flex-1">
        <Sidebar />
        <main class="flex-1 bg-slate-50 p-6 overflow-y-auto">
          <Outlet />
        </main>
      </div>
    </div>
  );
};

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<Login />} />
          <Route path="/setup-mfa" element={<SetupMFA />} />

          {/* Authenticated routes */}
          <Route element={<ProtectedRoute />}>
            <Route element={<AuthenticatedLayout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/profile" element={<Profile />} />
              
              <Route path="/documents/new" element={
                <ProtectedRoute requiredPermission="create_document" />
              }>
                <Route index element={<NewDocument />} />
              </Route>

              <Route path="/documents/:id" element={<DocumentDetail />} />
              <Route path="/documents/:id/sign" element={<SignDocument />} />

              <Route path="/admin" element={
                <ProtectedRoute requiredPermission="manage_users" />
              }>
                <Route index element={<AdminPanel />} />
              </Route>
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
      {/* Toast popup notifications layout config */}
      <Toaster position="top-right" toastOptions={{ duration: 4000 }} />
    </AuthProvider>
  );
}

export default App;
