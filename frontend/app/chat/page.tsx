"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getToken } from "@/lib/auth";
import Sidebar from "./SideBar";
import MessageList from "./MessageList";
import ChatBox from "./ChatBox";
import { queryRagStream, Source } from "@/lib/app";

export type Message = {
  role: "user" | "assistant";
  content: string;
  isStreaming?: boolean;
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
  const [isStreaming, setIsStreaming] = useState(false);

  useEffect(() => {
    const token = getToken();
    if (!token) router.push("/login");
  }, [router]);

  const handleSend = async (text: string) => {
    if (isStreaming) return;

    // Thêm tin nhắn user
    setMessages((prev) => [...prev, { role: "user", content: text }]);

    // Thêm placeholder cho assistant (đang stream)
    setMessages((prev) => [
      ...prev,
      { role: "assistant", content: "", isStreaming: true },
    ]);
    setIsStreaming(true);

    const token = localStorage.getItem("token") ?? "";

    await queryRagStream(
      text,
      token,
      // onToken: append từng chunk vào tin nhắn cuối
      (content) => {
        setMessages((prev) => {
          const updated = [...prev];
          const last = updated[updated.length - 1];
          updated[updated.length - 1] = {
            ...last,
            content: last.content + content,
          };
          return updated;
        });
      },
      // onDone: gắn sources + tắt streaming cursor
      (sources, usedK, processingTime) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...updated[updated.length - 1],
            isStreaming: false,
            meta: { processing_time: processingTime, used_k: usedK, sources },
          };
          return updated;
        });
        setIsStreaming(false);
      },
      // onError
      (error) => {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = {
            role: "assistant",
            content: `⚠️ ${error}`,
            isStreaming: false,
          };
          return updated;
        });
        setIsStreaming(false);
      }
    );
  };

  return (
    <div className="flex h-screen bg-gray-900 text-white">
      <Sidebar open={sidebarOpen} setOpen={setSidebarOpen} />
      <div className="flex flex-col flex-1">
        <div className="flex-1 overflow-y-auto p-4">
          <MessageList messages={messages} />
        </div>
        <ChatBox onSend={handleSend} disabled={isStreaming} />
      </div>
    </div>
  );
}
