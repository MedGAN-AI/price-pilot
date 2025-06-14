import React from 'react';
import type { ChatResponse } from '../../services/api';
import ProductGrid from '../products/ProductGrid';
import { extractProductsFromResponse } from '../../utils/productParser';

interface MessageBubbleProps {
  message: string;
  isUser: boolean;
  timestamp?: string;
  metadata?: Pick<ChatResponse, 'agent_used' | 'intent' | 'confidence'>;
}

const MessageBubble: React.FC<MessageBubbleProps> = ({ 
  message, 
  isUser, 
  timestamp,
  metadata 
}) => {
  const formatTime = (isoString: string) => {
    return new Date(isoString).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const getAgentEmoji = (agent: string) => {
    const agentEmojis: Record<string, string> = {
      'ChatAgent': '💬',
      'InventoryAgent': '📦',
      'RecommendAgent': '🎯',
      'OrderAgent': '🛒',
      'LogisticsAgent': '🚚',
      'ForecastAgent': '📈'
    };
    return agentEmojis[agent] || '🤖';
  };
  const getIntentColor = (intent: string) => {
    const colors: Record<string, string> = {
      'chat': 'text-primary-600',
      'inventory': 'text-emerald-600',
      'recommend': 'text-purple-600',
      'order': 'text-orange-600',
      'logistics': 'text-blue-600',
      'forecast': 'text-indigo-600'
    };
    return colors[intent] || 'text-secondary-600';
  };  // Extract products from bot messages (for OrderAgent and RecommendAgent)
  let products: any[] = [];
  try {
    if (!isUser && (metadata?.agent_used === 'RecommendAgent' || metadata?.agent_used === 'OrderAgent')) {
      products = extractProductsFromResponse(message);
    }
  } catch (error) {
    console.error('Error extracting products from message:', error);
    products = [];
  }

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 px-4`}>
      <div className="max-w-xs lg:max-w-2xl w-full">
        {/* Message bubble */}
        <div className={`
          ${isUser 
            ? 'message-bubble-user ml-auto animate-slide-up' 
            : 'message-bubble-bot animate-fade-in'
          }
          transition-all duration-300 hover:shadow-medium
        `}>
          <p className="text-sm leading-relaxed whitespace-pre-wrap break-words">
            {message}
          </p>
        </div>

        {/* Product recommendations for RecommendAgent */}
        {products.length > 0 && (
          <div className="mt-4">
            <ProductGrid 
              products={products}
              title="AI Recommendations"
            />
          </div>
        )}
        
        {/* Metadata for bot messages */}
        {!isUser && metadata && (
          <div className="flex items-center gap-2 mt-2 text-xs text-secondary-500 animate-fade-in">
            <div className="flex items-center gap-1">
              <span className="text-sm">{getAgentEmoji(metadata.agent_used)}</span>
              <span className="font-medium">{metadata.agent_used}</span>
            </div>
            <span className="text-secondary-300">•</span>
            <div className="flex items-center gap-1">
              <span className={`font-medium ${getIntentColor(metadata.intent)}`}>
                {metadata.intent}
              </span>
              <span className="text-secondary-400">
                ({Math.round(metadata.confidence * 100)}%)
              </span>
            </div>
          </div>
        )}
        
        {/* Timestamp */}
        {timestamp && (
          <div className={`
            text-xs text-secondary-400 mt-1 
            ${isUser ? 'text-right' : 'text-left'}
            animate-fade-in
          `}>
            {formatTime(timestamp)}
          </div>
        )}
      </div>
    </div>
  );
};

export default MessageBubble;
