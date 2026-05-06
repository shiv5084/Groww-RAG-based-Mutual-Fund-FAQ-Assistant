'use client';

import { useState, useEffect, useRef } from 'react';
import apiClient, { ApiError } from '@/utils/api-client';
import { Thread, Message, AssistantResponse } from '@/types/api';

const EXAMPLE_QUESTIONS = [
  "What is HDFC Large Cap Fund?",
  "What are the different types of mutual funds?",
  "What is the lock-in period for ELSS?",
];
export default function HomePage() {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [currentThread, setCurrentThread] = useState<Thread | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Create new thread
  const createNewThread = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const thread = await apiClient.createThread();
      setCurrentThread(thread);
      setMessages([]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to create new chat');
    } finally {
      setIsLoading(false);
    }
  };

  // PII Detection Patterns
  const PII_PATTERNS = {
    PAN: /[A-Z]{5}[0-9]{4}[A-Z]{1}/i,
    AADHAAR: /\b[2-9][0-9]{3}\s?[0-9]{4}\s?[0-9]{4}\b/,
    PHONE: /\b[6-9][0-9]{9}\b/,
    EMAIL: /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/,
    ACCOUNT: /\b[0-9]{9,18}\b/
  };

  const detectPII = (text: string): string[] => {
    const found: string[] = [];
    if (PII_PATTERNS.PAN.test(text)) found.push('PAN Card');
    if (PII_PATTERNS.AADHAAR.test(text)) found.push('Aadhaar Number');
    if (PII_PATTERNS.PHONE.test(text)) found.push('Phone Number');
    if (PII_PATTERNS.EMAIL.test(text)) found.push('Email Address');
    // Account number is tricky, only flag if it's very likely
    if (PII_PATTERNS.ACCOUNT.test(text) && !PII_PATTERNS.AADHAAR.test(text)) found.push('Bank Account Number');
    return found;
  };

  // Send message
  const sendMessage = async (message: string) => {
    if (!currentThread || isLoading) return;

    // PII Check
    const detectedPII = detectPII(message);
    if (detectedPII.length > 0) {
      setError(`Security Warning: Please remove sensitive information (${detectedPII.join(', ')}) before sending.`);
      return;
    }

    try {
      setIsLoading(true);
      setError(null);

      // Add user message to UI immediately
      const userMessage: Message = {
        id: `temp-${Date.now()}`,
        thread_id: currentThread.thread_id,
        role: 'user',
        content: message,
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMessage]);

      // Send to backend
      const response: AssistantResponse = await apiClient.sendMessage(
        currentThread.thread_id,
        { user_message: message }
      );

      // Add assistant response
      const assistantMessage: Message = {
        id: response.message_id,
        thread_id: currentThread.thread_id,
        role: 'assistant',
        content: response.assistant_message,
        timestamp: response.last_updated,
        citation_url: response.citation_url,
      };
      setMessages(prev => [...prev, assistantMessage]);

    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Failed to send message');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle example question click
  const handleExampleQuestion = (question: string) => {
    if (!currentThread) {
      createNewThread().then(() => {
        setTimeout(() => setInputMessage(question), 100);
      });
    } else {
      setInputMessage(question);
    }
  };

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (inputMessage.trim()) {
      sendMessage(inputMessage.trim());
      setInputMessage('');
    }
  };

  // Auto-create thread on first interaction
  useEffect(() => {
    if (!currentThread && messages.length === 0) {
      createNewThread();
    }
  }, []);

  return (
    <div
      className="h-screen flex flex-col bg-cover bg-center bg-fixed relative overflow-hidden"
      style={{ backgroundImage: "url('/screen.png')" }}
    >
      {/* Overlay to dim the background for better readability */}
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]"></div>

      <div className="relative z-10 flex flex-col h-full">
        {/* Header - Fixed at Top */}
        <header className="bg-white/95 backdrop-blur-md border-b border-green-100 shadow-sm flex-shrink-0">
          <div className="max-w-4xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <img src="/groww_logo.png" alt="Groww Logo" className="h-10 w-10 object-contain" />
                <div>
                  <h1 className="text-2xl font-bold text-green-900">
                    Groww Mutual Fund FAQ Assistant
                  </h1>
                  <p className="text-sm text-green-700">
                    Factual information about mutual funds
                  </p>
                </div>
              </div>
              <button
                onClick={createNewThread}
                disabled={isLoading}
                className="px-6 py-2 bg-green-800 text-white rounded-xl hover:bg-green-900 transition-all shadow-lg hover:shadow-green-900/20 disabled:opacity-50 font-semibold"
              >
                New Chat
              </button>
            </div>
          </div>
        </header>

        {/* Main Content - Scrollable Area */}
        <main className="flex-1 overflow-y-auto custom-scrollbar">
          <div className="max-w-4xl w-full mx-auto px-4 py-8 sm:px-6 lg:px-8 flex flex-col min-h-full">
            {/* Welcome Section */}
            {messages.length === 0 && (
              <div className="text-center py-12 bg-green-50/90 backdrop-blur-lg rounded-3xl shadow-2xl p-10 border border-green-200/50 my-auto">
                <h2 className="text-4xl font-extrabold text-green-900 mb-6">
                  Welcome to Groww Mutual Fund FAQ Assistant
                </h2>
                <p className="text-xl text-green-800 mb-10 max-w-2xl mx-auto leading-relaxed">
                  Get factual information about mutual funds, investment processes, and financial concepts.
                  This assistant provides educational content only and does not give investment advice.
                </p>

                {/* Example Questions */}
                <div className="space-y-6">
                  <p className="text-sm font-bold text-green-700 uppercase tracking-wider">
                    Try asking these questions:
                  </p>
                  <div className="flex flex-col sm:flex-row gap-4 justify-center">
                    {EXAMPLE_QUESTIONS.map((question, index) => (
                      <button
                        key={index}
                        onClick={() => handleExampleQuestion(question)}
                        className="px-6 py-4 bg-green-800 text-white rounded-2xl hover:bg-green-900 transition-all shadow-xl hover:scale-105 active:scale-95 font-medium text-sm flex-1 max-w-xs border border-green-700"
                      >
                        {question}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Chat Messages */}
            {messages.length > 0 && (
              <div className="space-y-6 pb-4">
                {messages.map((message) => (
                  <div
                    key={message.id}
                    className={`p-5 rounded-3xl shadow-xl border animate-in fade-in slide-in-from-bottom-4 duration-500 ${message.role === 'user'
                        ? 'bg-green-800 text-white ml-auto max-w-[85%] border-green-700'
                        : 'bg-white/95 backdrop-blur-sm text-gray-900 mr-auto max-w-[85%] border-green-100'
                      }`}
                  >
                    <div className="flex items-start space-x-4">
                      <div className="flex-shrink-0">
                        <div className={`w-10 h-10 rounded-2xl flex items-center justify-center text-sm font-bold shadow-inner ${message.role === 'user'
                            ? 'bg-white text-green-800'
                            : 'bg-green-800 text-white'
                          }`}>
                          {message.role === 'user' ? 'U' : 'A'}
                        </div>
                      </div>
                      <div className="flex-1 overflow-hidden">
                        <p className={`whitespace-pre-wrap leading-relaxed text-lg ${message.role === 'user' ? 'text-green-50' : 'text-gray-800'}`}>
                          {message.content}
                        </p>
                        {message.citation_url && (
                          <div className="mt-4 pt-4 border-t border-green-100/20">
                            <a
                              href={message.citation_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="bg-green-100/10 hover:bg-green-100/20 px-4 py-2 rounded-xl text-green-700 hover:text-green-900 text-xs font-bold flex items-center gap-2 w-fit transition-all group"
                            >
                              <span>Official Source</span>
                              <svg className="w-4 h-4 group-hover:translate-x-1 transition-transform" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                              </svg>
                            </a>
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                ))}
                {isLoading && (
                  <div className="bg-white/95 backdrop-blur-sm p-6 rounded-3xl shadow-xl border border-green-100 mr-auto max-w-[80%] flex items-center space-x-3">
                    <div className="flex space-x-1">
                      <div className="w-3 h-3 bg-green-600 rounded-full animate-bounce"></div>
                      <div className="w-3 h-3 bg-green-600 rounded-full animate-bounce [animation-delay:-.3s]"></div>
                      <div className="w-3 h-3 bg-green-600 rounded-full animate-bounce [animation-delay:-.5s]"></div>
                    </div>
                    <span className="text-green-700 font-medium text-sm">Assistant is thinking...</span>
                  </div>
                )}
                {/* Scroll Anchor */}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>
        </main>

        {/* Input Form - Fixed at Bottom */}
        <div className="bg-gradient-to-t from-black/40 via-black/10 to-transparent p-6 flex-shrink-0">
          <div className="max-w-4xl mx-auto">
            {error && (
              <div className="mb-4 bg-red-600 text-white px-8 py-4 rounded-2xl shadow-2xl animate-in zoom-in duration-300">
                <div className="flex items-center space-x-3">
                  <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-sm font-bold">{error}</p>
                </div>
              </div>
            )}
            {currentThread && (
              <form onSubmit={handleSubmit} className="relative group">
                <input
                  type="text"
                  value={inputMessage}
                  onChange={(e) => setInputMessage(e.target.value)}
                  placeholder="Ask about mutual funds..."
                  className="w-full bg-white/95 backdrop-blur-xl border-2 border-green-100 rounded-3xl px-8 py-5 pr-24 shadow-2xl focus:border-green-500 focus:ring-4 focus:ring-green-500/20 focus:outline-none text-gray-900 placeholder:text-gray-400 text-lg transition-all"
                  disabled={isLoading}
                />
                <button
                  type="submit"
                  disabled={isLoading || !inputMessage.trim()}
                  className="absolute right-3 top-3 bottom-3 px-8 bg-green-800 text-white rounded-2xl hover:bg-green-900 transition-all shadow-lg hover:shadow-green-900/40 disabled:opacity-50 flex items-center justify-center border border-green-700 group-hover:scale-[1.02]"
                >
                  {isLoading ? (
                    <div className="w-6 h-6 border-3 border-white/30 border-t-white rounded-full animate-spin"></div>
                  ) : (
                    <div className="flex items-center space-x-2">
                      <span className="font-bold">Send</span>
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 5l7 7-7 7M5 5l7 7-7 7" />
                      </svg>
                    </div>
                  )}
                </button>
              </form>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
