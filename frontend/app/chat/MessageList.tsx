"use client";

import type { Message } from "./page";

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
          {/* Message content + streaming cursor */}
          <p className="whitespace-pre-wrap">
            {m.content}
            {m.isStreaming && (
              <span className="inline-block w-2 h-4 bg-gray-300 animate-pulse ml-0.5 align-middle rounded-sm" />
            )}
          </p>

          {/* Sources + metadata – chỉ hiện khi stream xong */}
          {m.role === "assistant" && !m.isStreaming && m.meta && (
            <div className="mt-3 text-sm text-gray-300 border-t border-gray-600 pt-2">
              <p>
                ⏱️ {m.meta.processing_time}s | 📄 {m.meta.used_k} docs
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
                        className="text-blue-400 hover:underline break-all"
                      >
                        {src.url}
                      </a>
                      {/* Rerank score (ưu tiên) */}
                      {src.rerank_score != null && (
                        <span className="ml-2 text-green-400">
                          rerank: {src.rerank_score.toFixed(3)}
                        </span>
                      )}
                      {/* RRF score */}
                      {src.rrf_score != null && (
                        <span className="ml-2 text-yellow-400">
                          rrf: {src.rrf_score.toFixed(4)}
                        </span>
                      )}
                      {/* FAISS similarity */}
                      {src.similarity_score != null && (
                        <span className="ml-2 text-gray-400">
                          sim: {src.similarity_score.toFixed(4)}
                        </span>
                      )}
                      {src.snippet && (
                        <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">
                          {src.snippet}
                        </p>
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
