"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { signup } from "@/lib/app";

export default function SignupPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [message, setMessage] = useState("");

  const handleSignup = async () => {
    if (password !== confirmPassword) {
      setMessage("Confirm password do not match!");
      return;
    }

    try {
      const res = await signup(username, password, confirmPassword);
      setMessage("Sign up successfully!");
      // Sau khi đăng ký xong thì điều hướng sang trang login
      router.push("/login");
    } catch (err: any) {
      setMessage("Sign up error: " + (err.response?.data?.detail || err.message));
    }
  };

  return (
    <div className="flex flex-col items-center justify-center min-h-screen gap-4">
      <h1 className="text-2xl font-bold">Sign Up</h1>
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
      <input
        className="border px-2 py-1"
        type="password"
        placeholder="Confirm Password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
      />
      <button
        onClick={handleSignup}
        className="bg-blue-500 text-white px-4 py-2 rounded"
      >
        Đăng ký
      </button>
      {message && <p>{message}</p>}
    </div>
  );
}
