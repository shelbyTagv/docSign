import React from "react";
import { NavLink } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const Sidebar = () => {
  const { hasPermission } = useAuth();

  const links = [
    {
      to: "/",
      label: "Dashboard",
      icon: (
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l2-2m0 0l7-7 7 7M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" />
        </svg>
      ),
    },
    {
      to: "/documents/new",
      label: "New Document",
      icon: (
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
        </svg>
      ),
      permission: "create_document",
    },
    {
      to: "/profile",
      label: "My Profile",
      icon: (
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
        </svg>
      ),
    },
    {
      to: "/admin",
      label: "System Admin",
      icon: (
        <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
        </svg>
      ),
      permission: "manage_users",
    },
  ];

  return (
    <aside class="w-64 bg-slate-900 text-slate-300 min-h-[calc(100vh-4rem)] flex-shrink-0 flex flex-col border-r border-slate-800">
      <div class="flex-1 py-6 space-y-1 px-4">
        {links.map((link) => {
          if (link.permission && !hasPermission(link.permission)) {
            return null;
          }

          return (
            <NavLink
              key={link.to}
              to={link.to}
              className={({ isActive }) =>
                `flex items-center space-x-3 px-4 py-3 rounded-md text-sm font-medium transition-all duration-150 ${
                  isActive
                    ? "bg-brand-800 text-white shadow-sm"
                    : "text-slate-400 hover:bg-slate-800 hover:text-slate-200"
                }`
              }
            >
              {link.icon}
              <span>{link.label}</span>
            </NavLink>
          );
        })}
      </div>
      <div class="p-4 border-t border-slate-800 text-center">
        <p class="text-xs text-slate-500 font-medium">Enterprise DocSign Platform</p>
        <p class="text-[10px] text-slate-600 mt-1">v1.0.0 Stable</p>
      </div>
    </aside>
  );
};

export default Sidebar;
