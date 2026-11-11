
import axios from "axios";

const api = axios.create({
  baseURL:
    import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

// Attach the login token to API requests when available.
api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem("access_token");

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// ---- Login session helpers (kept in sessionStorage: cleared when the tab closes) ----
export const saveSession = (result) => {
  sessionStorage.setItem("access_token", result.access_token);
  sessionStorage.setItem(
    "user",
    JSON.stringify({
      id: result.user_id,
      full_name: result.full_name,
      role: result.role,
    })
  );
};

export const getSession = () => {
  let user = null;
  try {
    user = JSON.parse(sessionStorage.getItem("user") || "null");
  } catch (_) {
    user = null;
  }
  return { token: sessionStorage.getItem("access_token"), user };
};

export const clearSession = () => {
  sessionStorage.removeItem("access_token");
  sessionStorage.removeItem("user");
};

// If the server says the token is missing/expired, log the user out and go to Login.
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || "";
    const isAuthCall = url.startsWith("/auth/login") || url.startsWith("/auth/register");
    if (error.response?.status === 401 && !isAuthCall) {
      clearSession();
      if (window.location.pathname !== "/login") {
        window.location.assign("/login?expired=1");
      }
    }
    return Promise.reject(error);
  }
);

export const checkBackendHealth = async () => {
  const response = await api.get("/health");
  return response.data;
};

export const registerUser = async (userData) => {
  const response = await api.post("/auth/register", userData);
  return response.data;
};

export const loginUser = async (credentials) => {
  const response = await api.post("/auth/login", credentials);
  return response.data;
};

export default api;
