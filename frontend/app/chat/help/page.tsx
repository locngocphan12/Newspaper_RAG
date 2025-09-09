// app/chat/help/page.tsx
"use client";

import Link from "next/link";
import { Mail, Facebook } from "lucide-react";

export default function HelpPage() {
  return (
    <div className="h-screen bg-gray-900 text-white flex flex-col items-center justify-center p-6">
      <h1 className="text-3xl font-bold mb-6">Hỗ trợ</h1>

      <div className="space-y-4 text-lg">
        <p>Nếu bạn gặp vấn đề, vui lòng liên hệ:</p>

        <div className="flex items-center gap-2">
          <Mail />
          <span>Gmail: <a href="locngocphan12@gmail.com" className="text-blue-400 hover:underline">locngocphan12@gmail.com</a></span>
        </div>

        <div className="flex items-center gap-2">
          <Facebook />
          <span>
            Facebook:{" "}
            <Link
              href="https://facebook.com/ngocppl.uit"
              target="_blank"
              className="text-blue-400 hover:underline"
            >
              facebook.com/ngocppl.uit
            </Link>
          </span>
        </div>
      </div>

      <Link
        href="/chat"
        className="mt-8 px-4 py-2 bg-blue-600 hover:bg-blue-700 rounded-lg"
      >
        ⬅️ Quay lại Chat
      </Link>
    </div>
  );
}
