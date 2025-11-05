import ChatInterface from "@/components/ChatInterface";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 bg-gradient-to-br from-blue-50 via-white to-purple-50 dark:from-gray-900 dark:via-gray-800 dark:to-gray-900">
      <div className="w-full max-w-4xl">
        <div className="mb-6 text-center">
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white mb-2">
            Pydantic AI Chat
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Powered by Pydantic AI, Mem0, and Langfuse
          </p>
        </div>
        <ChatInterface />
      </div>
    </main>
  );
}
