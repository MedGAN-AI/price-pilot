import React, { useState, useRef, useEffect } from 'react';
import { apiService, type ChatRequest, type ChatResponse } from '../../services/api';
import MessageBubble from './MessageBubble';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import ProductGrid from '../products/ProductGrid';
import RealProductsCatalog from '../products/RealProductsCatalog';
import { createSampleProducts, extractProductsFromResponse } from '../../utils/productParser';

interface ChatMessage {
  id: string;
  message: string;
  isUser: boolean;
  timestamp: string;
  metadata?: Pick<ChatResponse, 'agent_used' | 'intent' | 'confidence'>;
}

const ChatInterface: React.FC = () => {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      message: "Hi! I'm your Price Pilot assistant. I can help you with product recommendations, inventory checks, order tracking, and more. How can I assist you today?",
      isUser: false,
      timestamp: new Date().toISOString(),
      metadata: {
        agent_used: 'ChatAgent',
        intent: 'greeting',
        confidence: 1.0
      }
    }
  ]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId] = useState(`session_${Date.now()}`);
  const [showSampleProducts, setShowSampleProducts] = useState(false);
  const [showRealProducts, setShowRealProducts] = useState(false);
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);  const sendMessage = async (messageText?: string) => {
    const textToSend = messageText || inputMessage.trim();
    if (!textToSend || isLoading) return;

    // Special handling for sample products
    if (textToSend.toLowerCase().includes('sample products')) {
      setShowSampleProducts(true);
      setInputMessage('');
      return;
    }

    // Special handling for real products
    if (textToSend.toLowerCase().includes('real products')) {
      setShowRealProducts(true);
      setInputMessage('');
      return;
    }

    const userMessage: ChatMessage = {
      id: `user_${Date.now()}`,
      message: textToSend,
      isUser: true,
      timestamp: new Date().toISOString()
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);
    setError(null);    try {
      const request: ChatRequest = {
        message: textToSend,
        session_id: sessionId
      };      const response = await apiService.sendMessage(request);
      
      // Validate response structure
      if (!response || !response.response) {
        throw new Error('Invalid response from backend');
      }
      
      const botMessage: ChatMessage = {
        id: response.session_id + '_' + Date.now(),
        message: response.response,
        isUser: false,
        timestamp: response.timestamp || new Date().toISOString(),
        metadata: {
          agent_used: response.agent_used || 'Unknown',
          intent: response.intent || 'unknown',
          confidence: response.confidence || 0
        }
      };

      // Check if the response contains product information for better display
      try {
        const extractedProducts = extractProductsFromResponse(response.response);
        if (extractedProducts.length > 0) {
          console.log('🛍️ Found products in chat response:', extractedProducts);
        }
      } catch (productError) {        console.error('Error extracting products:', productError);
      }

      setMessages(prev => [...prev, botMessage]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const retryLastMessage = () => {
    const lastUserMessage = [...messages].reverse().find(msg => msg.isUser);
    if (lastUserMessage) {
      sendMessage(lastUserMessage.message);
    }
  };

  const clearChat = () => {
    setMessages([{
      id: 'welcome_new',
      message: "Chat cleared! How can I help you?",
      isUser: false,
      timestamp: new Date().toISOString(),
      metadata: {
        agent_used: 'ChatAgent',
        intent: 'greeting',
        confidence: 1.0
      }
    }]);
    setError(null);
  };  // Quick action buttons
  const quickActions = [
    { text: "What products do you have?", icon: "🛍️" },
    { text: "Show me real products", icon: "🎁" },
    { text: "Show me sample products", icon: "🎨" },
    { text: "Check inventory", icon: "�" },
    { text: "Track my order", icon: "🚚" }
  ];

  return (
    <div className="max-w-4xl mx-auto h-screen flex flex-col bg-gradient-to-br from-secondary-50 via-white to-primary-50">
      {/* Modern Header */}
      <div className="card border-0 rounded-none border-b border-secondary-200 backdrop-blur-lg bg-white/95">
        <div className="flex justify-between items-center p-6">
          <div className="animate-fade-in">
            <h1 className="text-2xl font-bold bg-gradient-to-r from-primary-600 to-primary-700 bg-clip-text text-transparent">
              🚀 Price Pilot Assistant
            </h1>
            <p className="text-sm text-secondary-500 mt-1">
              Powered by Multi-Agent AI • Session: 
              <span className="font-mono text-xs bg-secondary-100 px-2 py-1 rounded-md ml-2">
                {sessionId.slice(-8)}
              </span>
            </p>
          </div>
          <button
            onClick={clearChat}
            className="btn-secondary text-xs hover:scale-105 transition-transform duration-200"
          >
            🗑️ Clear Chat
          </button>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-secondary-300 scrollbar-track-secondary-100">
        {messages.map((msg) => (
          <div key={msg.id} className="animate-fade-in">
            <MessageBubble
              message={msg.message}
              isUser={msg.isUser}
              timestamp={msg.timestamp}
              metadata={msg.metadata}
            />
          </div>
        ))}
        
        {/* Loading indicator */}
        {isLoading && (
          <div className="flex justify-start animate-slide-up">
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl rounded-bl-md px-4 py-3 shadow-soft border border-secondary-100">
              <LoadingSpinner size="small" message="Agent is thinking..." />
            </div>
          </div>
        )}
          {/* Error message */}
        {error && (
          <div className="animate-slide-up">
            <ErrorMessage 
              message={error}
              onRetry={retryLastMessage}
              onDismiss={() => setError(null)}
            />
          </div>
        )}        {/* Sample Products Display */}
        {showSampleProducts && (
          <div className="animate-fade-in">
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-soft border border-secondary-100">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-secondary-800">
                  � Sample Products - Demo Shopping Cart
                </h3>
                <button
                  onClick={() => setShowSampleProducts(false)}
                  className="text-secondary-500 hover:text-secondary-700 transition-colors duration-200"
                >
                  ✕
                </button>
              </div>
              <ProductGrid 
                products={createSampleProducts()}
                title="Demo Products (Not Real)"
              />
            </div>
          </div>
        )}

        {/* Real Products Display */}
        {showRealProducts && (
          <div className="animate-fade-in">
            <div className="bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-soft border border-secondary-100">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-secondary-800">
                  🛍️ Real Products from Backend
                </h3>
                <button
                  onClick={() => setShowRealProducts(false)}
                  className="text-secondary-500 hover:text-secondary-700 transition-colors duration-200"
                >
                  ✕
                </button>
              </div>
              <RealProductsCatalog />
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions (show only when few messages) */}
      {messages.length <= 1 && (
        <div className="px-6 py-4 bg-white/80 backdrop-blur-sm border-t border-secondary-200">
          <p className="text-sm text-secondary-500 mb-3 font-medium">
            ⚡ Quick actions:
          </p>
          <div className="flex flex-wrap gap-2">
            {quickActions.map((action) => (
              <button
                key={action.text}
                onClick={() => sendMessage(action.text)}
                disabled={isLoading}
                className="btn-secondary text-sm py-2 px-3 hover:shadow-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                <span className="text-base">{action.icon}</span>
                <span>{action.text}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Modern Input Area */}
      <div className="p-6 bg-white/95 backdrop-blur-lg border-t border-secondary-200">
        <div className="flex gap-3 items-end">
          <div className="flex-1 relative">
            <input
              ref={inputRef}
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Type your message here..."
              disabled={isLoading}
              className="input-field pr-12 disabled:opacity-50 disabled:cursor-not-allowed"
            />
            {/* Character count indicator */}
            {inputMessage.length > 50 && (
              <div className="absolute right-3 top-1/2 transform -translate-y-1/2 text-xs text-secondary-400">
                {inputMessage.length}
              </div>
            )}
          </div>
          
          <button
            onClick={() => sendMessage()}
            disabled={!inputMessage.trim() || isLoading}
            className="w-12 h-12 rounded-xl bg-gradient-to-r from-primary-500 to-primary-600 text-white disabled:from-secondary-300 disabled:to-secondary-400 disabled:cursor-not-allowed transition-all duration-200 transform hover:scale-105 active:scale-95 shadow-medium hover:shadow-large flex items-center justify-center group"
          >
            {isLoading ? (
              <div className="animate-spin text-lg">⏳</div>
            ) : (
              <span className="text-lg group-hover:animate-bounce-subtle">🚀</span>
            )}
          </button>
        </div>
        
        <p className="text-xs text-secondary-400 text-center mt-3">
          Press <kbd className="px-2 py-1 bg-secondary-100 rounded text-secondary-600 font-mono">Enter</kbd> to send • 
          The AI will coordinate with specialized agents based on your request
        </p>
      </div>
    </div>
  );
};

export default ChatInterface;
