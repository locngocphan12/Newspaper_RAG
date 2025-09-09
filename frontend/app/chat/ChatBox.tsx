"use client";
import { useState } from "react";

export default function ChatBox({ onSend }: { onSend: (text: string) => void }) {
  const [text, setText] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!text.trim()) return;
    onSend(text);
    setText("");
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="p-3 border-t border-gray-700 bg-gray-950 flex"
    >
      <input
        type="text"
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Nhập tin nhắn..."
        className="flex-1 p-2 rounded-lg bg-gray-800 text-white focus:outline-none"
      />
      <button
        type="submit"
        className="ml-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 text-white"
      >
        Gửi
      </button>
    </form>
  );
}
