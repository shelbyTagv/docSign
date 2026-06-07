import React, { useState, useEffect } from "react";
import { useForm } from "react-hook-form";
import { getAllUsersApi, getAllRolesApi, assignRoleApi } from "../api/users";
import { registerUserApi } from "../api/auth";
import toast from "react-hot-toast";

const AdminPanel = () => {
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [assigning, setAssigning] = useState(false);

  // States to map selected role assignments
  const [selectedUser, setSelectedUser] = useState("");
  const [selectedRole, setSelectedRole] = useState("");

  const { register, handleSubmit, reset, formState: { errors } } = useForm();

  const fetchAdminData = async () => {
    try {
      setLoading(true);
      const [usersData, rolesData] = await Promise.all([
        getAllUsersApi(),
        getAllRolesApi(),
      ]);
      setUsers(usersData);
      setRoles(rolesData);
    } catch (err) {
      toast.error("Failed to fetch administrative data logs");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  const handleRegisterUser = async (data) => {
    setSubmitting(true);
    try {
      await registerUserApi(data);
      toast.success("User account registered successfully");
      reset();
      fetchAdminData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "User registration failed");
    } finally {
      setSubmitting(false);
    }
  };

  const handleAssignRole = async (e) => {
    e.preventDefault();
    if (!selectedUser || !selectedRole) {
      toast.error("Please select both user and role target options");
      return;
    }

    setAssigning(true);
    try {
      await assignRoleApi(selectedUser, selectedRole);
      toast.success("Role successfully assigned to user");
      setSelectedUser("");
      setSelectedRole("");
      fetchAdminData();
    } catch (err) {
      toast.error(err.response?.data?.detail || "Role assignment transaction failed");
    } finally {
      setAssigning(false);
    }
  };

  if (loading) {
    return (
      <div class="min-h-screen flex items-center justify-center bg-slate-50">
        <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-800"></div>
      </div>
    );
  }

  return (
    <div class="max-w-7xl mx-auto py-8 px-4 sm:px-6 lg:px-8 space-y-8">
      <div>
        <h1 class="text-2xl font-extrabold text-slate-900">System Admin Control</h1>
        <p class="text-sm text-slate-500 font-medium">Manage user credentials, enroll roles, and verify identity stamps.</p>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
        {/* Left Side: Create User Form */}
        <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
          <h2 class="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 mb-4 uppercase tracking-wider">Enroll New User</h2>
          <form onSubmit={handleSubmit(handleRegisterUser)} class="space-y-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Full Name</label>
              <input
                type="text"
                {...register("full_name", { required: "Name is required" })}
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-xs bg-slate-50"
              />
              {errors.full_name && <p class="mt-1 text-xs text-red-600">{errors.full_name.message}</p>}
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Email Address</label>
              <input
                type="email"
                {...register("email", { required: "Email is required" })}
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-xs bg-slate-50"
              />
              {errors.email && <p class="mt-1 text-xs text-red-600">{errors.email.message}</p>}
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Title / Designation</label>
              <input
                type="text"
                {...register("title")}
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-xs bg-slate-50"
                placeholder="e.g. Legal Counsel"
              />
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Department</label>
              <input
                type="text"
                {...register("department")}
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-xs bg-slate-50"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              class="w-full flex justify-center py-2 px-4 border border-transparent rounded shadow-sm text-xs font-bold uppercase tracking-wider text-white bg-brand-800 hover:bg-brand-700 disabled:bg-slate-300"
            >
              {submitting ? "Registering..." : "Register Account"}
            </button>
          </form>
        </div>

        {/* Center: Assign Role Panel */}
        <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm">
          <h2 class="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 mb-4 uppercase tracking-wider">Assign Role Permissions</h2>
          <form onSubmit={handleAssignRole} class="space-y-4">
            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Select Target User</label>
              <select
                value={selectedUser}
                onChange={(e) => setSelectedUser(e.target.value)}
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-xs bg-slate-50"
              >
                <option value="">-- Choose User --</option>
                {users.map((u) => (
                  <option key={u.id} value={u.id}>
                    {u.full_name} ({u.email})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label class="block text-xs font-semibold text-slate-500 uppercase tracking-wider">Select Role Type</label>
              <select
                value={selectedRole}
                onChange={(e) => setSelectedRole(e.target.value)}
                class="mt-1 block w-full px-3 py-2 border border-slate-300 rounded shadow-sm focus:outline-none focus:ring-brand-800 focus:border-brand-800 sm:text-xs bg-slate-50"
              >
                <option value="">-- Choose Role --</option>
                {roles.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name.toUpperCase()} (ID: {r.id})
                  </option>
                ))}
              </select>
            </div>

            <button
              type="submit"
              disabled={assigning}
              class="w-full flex justify-center py-2 px-4 border border-transparent rounded shadow-sm text-xs font-bold uppercase tracking-wider text-white bg-brand-800 hover:bg-brand-700 disabled:bg-slate-300"
            >
              {assigning ? "Assigning..." : "Assign Selected Role"}
            </button>
          </form>
        </div>

        {/* Right Side: Users Directory grid */}
        <div class="bg-white border border-slate-200 rounded-lg p-6 shadow-sm lg:col-span-1">
          <h2 class="text-sm font-bold text-slate-900 border-b border-slate-100 pb-3 mb-4 uppercase tracking-wider">Staff Directory</h2>
          
          <div class="space-y-4 max-h-[400px] overflow-y-auto pr-2">
            {users.map((u) => (
              <div key={u.id} class="border-b border-slate-100 pb-3 last:border-0">
                <p class="text-xs font-bold text-slate-800">{u.full_name}</p>
                <p class="text-[10px] text-slate-500">{u.email}</p>
                <p class="text-[10px] text-slate-400 italic">{u.title || "No Title"} • {u.department || "General"}</p>
                
                <div class="mt-2 flex flex-wrap gap-1.5">
                  {u.roles?.map((r) => (
                    <span key={r.id} class="px-1.5 py-0.5 rounded text-[8px] font-bold bg-brand-50 text-brand-800 uppercase tracking-widest border border-brand-100">
                      {r.name}
                    </span>
                  ))}
                  {u.identity_verified ? (
                    <span class="px-1.5 py-0.5 rounded text-[8px] font-bold bg-green-50 text-green-800 uppercase tracking-widest border border-green-100">
                      Signature OK
                    </span>
                  ) : (
                    <span class="px-1.5 py-0.5 rounded text-[8px] font-bold bg-amber-50 text-amber-800 uppercase tracking-widest border border-amber-100">
                      No Signature
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdminPanel;
