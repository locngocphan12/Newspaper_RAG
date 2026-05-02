import axios from "axios";

export const BACKEND_URL = "http://localhost:8031";

// Tạo một instance axios, set baseURL về backend FastAPI
const api = axios.create({
  baseURL: BACKEND_URL,
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

// Lấy history chat logs – trả về mảng trực tiếp
export const getHistory = async (token: string) => {
  const res = await api.get("/history", {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  // Backend trả về { total_returned, history: [...] } – lấy mảng history
  return Array.isArray(res.data) ? res.data : (res.data.history ?? []);
};

// =======================
// STREAMING QUERY API
// =======================

export type Source = {
  doc_id: number;
  url: string;
  section?: string;
  subsection?: string;
  similarity_score?: number | null;
  bm25_score?: number | null;
  rrf_score?: number | null;
  rerank_score?: number | null;
  snippet?: string;
};

/**
 * Streaming RAG query – dùng native fetch (không dùng axios vì axios không hỗ trợ streaming).
 * Gọi 3 callback:
 *   onToken(content)      – mỗi token LLM trả về
 *   onDone(sources, k, t) – khi stream kết thúc, nhận sources + metadata
 *   onError(msg)          – khi có lỗi
 */
export const queryRagStream = async (
  query: string,
  token: string,
  onToken: (content: string) => void,
  onDone: (sources: Source[], usedK: number, processingTime: number) => void,
  onError: (error: string) => void
): Promise<void> => {
  let response: Response;
  try {
    response = await fetch(`${BACKEND_URL}/query/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify({ query }),
    });
  } catch {
    onError("Không thể kết nối server. Vui lòng kiểm tra backend.");
    return;
  }

  if (!response.ok) {
    if (response.status === 401 || response.status === 403) {
      localStorage.removeItem("token");
      window.location.href = "/login";
      return;
    }
    onError(`Server lỗi HTTP ${response.status}`);
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? ""; // giữ dòng chưa complete trong buffer

    for (const line of lines) {
      if (!line.startsWith("data: ")) continue;
      try {
        const event = JSON.parse(line.slice(6));
        if (event.type === "token") {
          onToken(event.content as string);
        } else if (event.type === "done") {
          onDone(
            (event.sources as Source[]) ?? [],
            (event.used_k as number) ?? 0,
            (event.processing_time as number) ?? 0
          );
        } else if (event.type === "error") {
          onError((event.detail as string) ?? "Unknown error");
        }
      } catch {
        // ignore malformed SSE line
      }
    }
  }
};


