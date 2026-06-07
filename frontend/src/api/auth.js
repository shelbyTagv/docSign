import api from "./api";

export const loginApi = async (email, password) => {
  const response = await api.post("/auth/login", { email, password });
  return response.data;
};

export const verifyMfaApi = async (tempToken, code) => {
  const response = await api.post("/auth/verify-mfa", { temp_token: tempToken, code });
  return response.data;
};

export const getMfaSetupApi = async () => {
  const response = await api.get("/auth/mfa/setup");
  return response.data;
};

export const confirmMfaApi = async (code) => {
  const response = await api.post("/auth/mfa/confirm", { code });
  return response.data;
};

export const verifyMfaStandaloneApi = async (code) => {
  const response = await api.post("/auth/mfa/verify", { code });
  return response.data;
};

export const logoutApi = async () => {
  const response = await api.post("/auth/logout");
  localStorage.removeItem("accessToken");
  return response.data;
};

export const registerUserApi = async (userData) => {
  const response = await api.post("/auth/register", userData);
  return response.data;
};
