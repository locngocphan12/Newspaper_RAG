import "./globals.css";
import Link from "next/link";

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="vi">
      <body className="bg-gray-50 text-gray-900">
        {/* Header */}
        <header className="w-full bg-blue-600 text-white px-6 py-3 shadow">
          <div className="max-w-5xl mx-auto flex justify-between items-center">
            <Link href="/" className="text-xl font-bold">
              🚀 My RAG App
            </Link>
            <nav className="space-x-4">
              <Link href="/login" className="hover:underline">
                Đăng nhập
              </Link>
              <Link href="/signup" className="hover:underline">
                Đăng ký
              </Link>
              <Link href="/chat" className="hover:underline">
                Chat
              </Link>
            </nav>
          </div>
        </header>

        {/* Nội dung chính */}
        <main className="max-w-5xl mx-auto mt-8 px-4">{children}</main>
      </body>
    </html>
  );
}
