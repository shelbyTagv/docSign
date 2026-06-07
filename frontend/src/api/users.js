import api from "./api";

export const getMeApi = async () => {
  const response = await api.get("/users/me");
  return response.data;
};

export const updateMeApi = async (data) => {
  const response = await api.put("/users/me", data);
  return response.data;
};

export const uploadSignatureApi = async (image_base64, mfaToken) => {
  const response = await api.post("/users/me/signature", { image_base64 }, {
    headers: {
      "X-MFA-Token": mfaToken
    }
  });
  return response.data;
};

export const getSignaturePreviewApi = async () => {
  const response = await api.get("/users/me/signature/preview");
  return response.data;
};

export const changePasswordApi = async (data) => {
  const response = await api.post("/users/me/change-password", data);
  return response.data;
};

export const searchUsersApi = async (query) => {
  const response = await api.get("/users/search", { params: { q: query } });
  return response.data;
};

export const getAllUsersApi = async () => {
  const response = await api.get("/users/");
  return response.data;
};

export const assignRoleApi = async (userId, roleId) => {
  const response = await api.post(`/roles/${userId}/assign`, { role_id: roleId });
  return response.data;
};

export const getAllRolesApi = async () => {
  const response = await api.get("/roles/");
  return response.data;
};
