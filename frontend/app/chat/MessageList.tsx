"use client";

type Message = {
  role: "user" | "assistant";
  content: string;
  meta?: {
    processing_time: number;
    used_k: number;
    sources: { doc_id: number; url: string; score: number | null }[];
  };
};

export default function MessageList({ messages }: { messages: Message[] }) {
  return (
    <div className="space-y-3">
      {messages.map((m, i) => (
        <div
          key={i}
          className={`p-3 rounded-lg max-w-[70%] ${
            m.role === "user"
              ? "bg-blue-600 text-white ml-auto"
              : "bg-gray-800 text-gray-100 mr-auto"
          }`}
        >
          <p>{m.content}</p>


          {m.role === "assistant" && m.meta && (
            <div className="mt-3 text-sm text-gray-300 border-t border-gray-600 pt-2">
              <p>
                ⏱️ {m.meta.processing_time}s | 📊 {m.meta.used_k} docs
              </p>
              <div className="mt-2">
                <p className="font-semibold">📚 Nguồn tham khảo:</p>
                <ul className="list-disc ml-5 space-y-1">
                  {m.meta.sources.map((src) => (
                    <li key={src.doc_id}>
                      <a
                        href={src.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-blue-400 hover:underline"
                      >
                        {src.url}
                      </a>
                      {src.score !== null && (
                        <span className="ml-2 text-gray-400">
                          (độ liên quan: {src.score.toFixed(3)})
                        </span>
                      )}
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
