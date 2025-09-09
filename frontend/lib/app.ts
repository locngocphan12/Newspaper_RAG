import axios from "axios";

// Tạo một instance axios, set baseURL về backend FastAPI
const api = axios.create({
  baseURL: "http://localhost:8031",
  headers: {
    "Content-Type": "application/json",
  },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 || error.response?.status === 403) {
      localStorage.removeItem("token");
      window.location.href = "/login"; // redirect về login
    }
    return Promise.reject(error);
  }
);
// =======================
// AUTH APIs
// =======================

// Đăng ký user mới
export const signup = async (username: string, password: string, confirmPassword: string) => {
  const res = await api.post("/auth/signup", { username, password, confirm_password: confirmPassword});
  return res.data;
};

// Đăng nhập user, trả về access_token
export const login = async (username: string, password: string) => {
  const res = await api.post("/auth/login", { username, password });
  return res.data; // { access_token: "xxx", token_type: "bearer" }
};

// =======================
// QUERY APIs (yêu cầu token)
// =======================

// Hàm query đến RAG
export const queryRag = async (query: string, token: string) => {
    const res = await api.post(
        "/query",
        { query },
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
     );
    return res.data;
};

// Lấy history chat logs
export const getHistory = async (token: string) => {
  const res = await api.get("/history", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return res.data; // danh sách chat logs
};


