import api from "./api";

export const createDocumentApi = async (data) => {
  const response = await api.post("/documents/", data);
  return response.data;
};

export const getDocumentsApi = async (filter = "all") => {
  const response = await api.get("/documents/", { params: { filter } });
  return response.data;
};

export const getDocumentDetailApi = async (id) => {
  const response = await api.get(`/documents/${id}`);
  return response.data;
};

export const updateDocumentApi = async (id, data) => {
  const response = await api.put(`/documents/${id}`, data);
  return response.data;
};

export const setSignatoriesApi = async (id, signatories) => {
  const response = await api.post(`/documents/${id}/signatories`, signatories);
  return response.data;
};

export const sendDocumentApi = async (id) => {
  const response = await api.post(`/documents/${id}/send`);
  return response.data;
};

export const signDocumentApi = async (id, data, mfaToken) => {
  const response = await api.post(`/documents/${id}/sign`, data, {
    headers: {
      "X-MFA-Token": mfaToken
    }
  });
  return response.data;
};

export const recallDocumentApi = async (id) => {
  const response = await api.post(`/documents/${id}/recall`);
  return response.data;
};

export const getDocumentAuditTrailApi = async (id) => {
  const response = await api.get(`/documents/${id}/audit`);
  return response.data;
};

export const downloadDocumentPdfUrl = (id) => `/api/documents/${id}/download`;
