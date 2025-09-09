"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import Sidebar from "./SideBar";
import MessageList from "./MessageList";
import ChatBox from "./ChatBox";
import { queryRag, getHistory } from "@/lib/app";

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<
    { role: "user" | "assistant"; content: string }[]
  >([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Kiểm tra token khi load trang
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
    }
  }, [router]);

  // Hàm logout
  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  // Hàm gửi tin nhắn
  const handleSend = async (text: string) => {
    // Thêm tin nhắn user
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    try {
      const token = localStorage.getItem("token") || "";
      const data = await queryRag(text, token);
      setMessages((prev) => [
        ...prev,
        {
            role: "assistant",
            content: data.answer || "Không có câu trả lời",
            meta: {
            processing_time: data.processing_time,
            used_k: data.used_k,
            sources: data.sources,
            },
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Lỗi khi gọi RAG" },
      ]);
    }
  };


  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Sidebar */}
      <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} onLogout={handleLogout} />

      {/* Chat area */}
      <div className="flex flex-col flex-1">
        <div className="flex-1 overflow-y-auto p-4">
          <MessageList messages={messages} />
        </div>
        <ChatBox onSend={handleSend} />
      </div>
    </div>
  );
}
