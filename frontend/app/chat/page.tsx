"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import Sidebar from "./SideBar";
import MessageList from "./MessageList";
import ChatBox from "./ChatBox";
import { queryRag } from "@/lib/app";

type Source = {
  doc_id: number;
  url: string;
  section?: string;
  similarity_score?: number | null;
  rerank_score?: number | null;
  snippet?: string;
};

type Message = {
  role: "user" | "assistant";
  content: string;
  meta?: {
    processing_time: number;
    used_k: number;
    sources: Source[];
  };
};

export default function ChatPage() {
  const router = useRouter();
  const [messages, setMessages] = useState<Message[]>([]);
  const [sidebarOpen, setSidebarOpen] = useState(true);

  // Kiểm tra token khi load trang
  useEffect(() => {
    const token = getToken();
    if (!token) {
      router.push("/login");
    }
  }, [router]);

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
            processing_time: data.processing_time ?? 0,
            used_k: data.used_k ?? 0,
            sources: data.sources ?? [],
          },
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: "⚠️ Lỗi khi gọi RAG. Vui lòng thử lại." },
      ]);
    }
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      {/* Sidebar */}
      <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />

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
