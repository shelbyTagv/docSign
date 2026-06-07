import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { getMeApi } from "../api/users";
import { loginApi, verifyMfaApi, logoutApi } from "../api/auth";

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [accessToken, setAccessToken] = useState(localStorage.getItem("accessToken") || null);
  const [loading, setLoading] = useState(true);

  // Helper function to extract user details when access token changes
  const fetchCurrentUser = useCallback(async () => {
    try {
      setLoading(true);
      const data = await getMeApi();
      setUser(data);
    } catch (err) {
      console.error("Failed to load user profile on token setup:", err);
      setUser(null);
      localStorage.removeItem("accessToken");
      setAccessToken(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (accessToken) {
      fetchCurrentUser();
    } else {
      setLoading(false);
    }
  }, [accessToken, fetchCurrentUser]);

  // Listen for global unauthorized events dispatched by axios interceptor
  useEffect(() => {
    const handleUnauthorized = () => {
      setUser(null);
      setAccessToken(null);
      localStorage.removeItem("accessToken");
    };

    window.addEventListener("unauthorized", handleUnauthorized);
    return () => window.removeEventListener("unauthorized", handleUnauthorized);
  }, []);

  const login = async (email, password) => {
    const result = await loginApi(email, password);
    if (result.access_token) {
      localStorage.setItem("accessToken", result.access_token);
      setAccessToken(result.access_token);
    }
    return result;
  };

  const loginWithMfa = async (tempToken, code) => {
    const result = await verifyMfaApi(tempToken, code);
    if (result.access_token) {
      localStorage.setItem("accessToken", result.access_token);
      setAccessToken(result.access_token);
      setUser(result.user);
    }
    return result;
  };

  const logout = async () => {
    try {
      await logoutApi();
    } catch (err) {
      console.error("Logout request error:", err);
    } finally {
      setUser(null);
      setAccessToken(null);
      localStorage.removeItem("accessToken");
    }
  };

  const hasPermission = (permission) => {
    if (!user || !user.permissions) return false;
    return user.permissions.includes(permission);
  };

  const hasRole = (roleName) => {
    if (!user || !user.roles) return false;
    return user.roles.some((r) => r.name === roleName);
  };

  const value = {
    user,
    accessToken,
    loading,
    login,
    loginWithMfa,
    logout,
    hasPermission,
    hasRole,
    refreshUser: fetchCurrentUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
};
