// lib/auth.ts

export function getToken() {
  if (typeof window !== "undefined") {
    return localStorage.getItem("token");
  }
  return null;
}

export function parseJwt(token: string) {
  try {
    const base64Url = token.split(".")[1];
    if (!base64Url) return null;

    // JWT base64Url: thay '-' thành '+' và '_' thành '/'
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");

    // Giải mã từ base64 sang JSON
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => {
          return "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2);
        })
        .join("")
    );

    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error("parseJwt error:", e);
    return null;
  }
}