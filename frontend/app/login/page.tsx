"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/app";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [message, setMessage] = useState("");
  const router = useRouter();

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      router.push("/chat");
    }
  }, [router]);

  const handleLogin = async () => {
    try {
      const res = await login(username, password);
      // Lưu token vào localStorage để query RAG
      localStorage.setItem("token", res.access_token);
      // setMessage("Login thành công!");
      router.push("/chat");
    } catch (err: any) {
      setMessage("Login Failed: " + err.message);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <h1 className="text-2xl font-bold">Login</h1>
      <input
        className="border px-2 py-1"
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
      />
      <input
        className="border px-2 py-1"
        type="password"
        placeholder="Password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
      />
      <button
        onClick={handleLogin}
        className="bg-green-500 text-white px-4 py-2 rounded"
      >
        Đăng nhập
      </button>
      {message && <p>{message}</p>}
    </div>
  );
}
