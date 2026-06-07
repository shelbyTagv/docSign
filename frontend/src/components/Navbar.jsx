import React from "react";
import { useAuth } from "../context/AuthContext";

const Navbar = () => {
  const { user, logout } = useAuth();

  return (
    <nav class="bg-white border-b border-slate-200 h-16 flex items-center justify-between px-6 sticky top-0 z-30">
      <div class="flex items-center space-x-3">
        {/* Organization Branding */}
        <span class="text-xl font-bold text-brand-800 tracking-tight">DocSign</span>
        <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-brand-50 text-brand-800 border border-brand-100">
          Enterprise
        </span>
      </div>

      <div class="flex items-center space-x-4">
        <div class="text-right hidden sm:block">
          <p class="text-sm font-semibold text-slate-800">{user?.full_name}</p>
          <p class="text-xs text-slate-500 font-medium">{user?.title || "Officer"} • {user?.department || "Operations"}</p>
        </div>

        <div class="h-10 w-10 rounded-full bg-brand-800 text-white flex items-center justify-center font-bold border-2 border-brand-100 shadow-sm">
          {user?.full_name ? user.full_name.split(" ").map(n => n[0]).join("").substring(0, 2).toUpperCase() : "U"}
        </div>

        <button
          onClick={logout}
          class="inline-flex items-center justify-center p-2 rounded-md text-slate-500 hover:text-red-600 hover:bg-slate-50 transition-colors focus:outline-none"
          title="Sign Out"
        >
          <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
          </svg>
        </button>
      </div>
    </nav>
  );
};

export default Navbar;
