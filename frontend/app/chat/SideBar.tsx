"use client";
import { Menu, X, LogOut, HelpCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { getHistory } from "@/lib/app";
import { useEffect, useState } from "react";

export default function Sidebar({
  open,
  setOpen,
}: {
  open: boolean;
  setOpen: (open: boolean) => void;
}) {
  const router = useRouter();
  const [history, setHistory] = useState<
    { id: string; query: string; answer: string; timestamp: string }[]
  >([]);

  useEffect(() => {
    const token = localStorage.getItem("token") || "";
    if (token) {
      getHistory(token)
        .then((data) => setHistory(data))
        .catch(() => setHistory([]));
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem("token");
    router.push("/login");
  };

  const handleHelp = () => {
    router.push("/chat/help");
  };


  return (
    <div
      className={`${
        open ? "w-64" : "w-16"
      } bg-gray-900 text-white h-screen p-4 transition-all flex flex-col`}
    >
      {/* Header */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-lg font-bold">{open && "Chat History"}</h2>
        <button onClick={() => setOpen(!open)}>
          {open ? <X /> : <Menu />}
        </button>
      </div>

      {/* Nội dung sidebar (giả sử sau này là list history) */}
      <div className="flex-1 overflow-y-auto space-y-2">
        {open &&
          history.map((chat, idx) => (
            <div
              key={chat.timestamp || idx}
              className="p-2 bg-gray-800 rounded hover:bg-gray-700 cursor-pointer"
            >
              <p className="truncate text-sm">{chat.query}</p>
              <p className="text-xs text-gray-400">
                {new Date(chat.timestamp).toLocaleString()}
              </p>
            </div>
          ))}
        {open && history.length === 0 && (
          <p className="text-gray-400">Chưa có hội thoại nào</p>
        )}
      </div>

      {/* Nút Help */}
      <button
        onClick={handleHelp}
        className="mt-4 flex items-center gap-2 bg-blue-600 hover:bg-blue-700 px-3 py-2 rounded"
      >
        <HelpCircle size={18} />
        {open && "Help"}
      </button>

      {/* Nút Logout */}
      <button
        onClick={handleLogout}
        className="mt-4 flex items-center gap-2 bg-red-600 hover:bg-red-700 px-3 py-2 rounded"
      >
        <LogOut size={18} />
        {open && "Logout"}
      </button>
    </div>
  );
}
