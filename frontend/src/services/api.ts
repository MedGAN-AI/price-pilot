import axios, { AxiosError } from 'axios';

// Base configuration for our API
const API_BASE_URL = 'http://localhost:8000';

// Create axios instance with default config
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 2 minutes timeout for complex agent queries
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
apiClient.interceptors.request.use(
  (config) => {
    console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('❌ API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.status} ${response.config.url}`);
    return response;
  },
  (error: AxiosError) => {
    console.error('❌ API Response Error:', error.message);
    
    // Handle different error types
    if (error.code === 'ECONNABORTED') {
      throw new Error('Request timeout - The agent is taking longer than expected. Please try again.');
    } else if (error.response?.status === 500) {
      throw new Error('Server error - There was an issue with the backend. Please try again.');
    } else if (error.response?.status === 404) {
      throw new Error('Endpoint not found - Please check if the backend is running.');
    } else if (!error.response) {
      throw new Error('Network error - Please check if the backend is running on http://localhost:8000');
    }
    
    return Promise.reject(error);
  }
);

// Types for our API responses (TypeScript interfaces)
export interface ChatRequest {
  message: string;
  session_id?: string;
  user_context?: Record<string, any>;
}

export interface ChatResponse {
  response: string;
  session_id: string;
  intent: string;
  confidence: number;
  agent_used: string;
  timestamp: string;
  products?: ProductFromAPI[]; // Add products array for when agents return product data
}

export interface ProductFromAPI {
  sku: string;
  name: string;
  description: string;
  price: string; // Backend returns as string like "$79.99"
  category: string;
}

export interface HealthResponse {
  status: string;
  timestamp: string;
  version: string;
  agents_status: Record<string, string>;
}

// Enhanced error handling type
export interface ApiError {
  message: string;
  status?: number;
  code?: string;
}

// Retry utility function
const retryRequest = async <T>(
  requestFn: () => Promise<T>,
  maxRetries: number = 5, // Increased from 2 to 5 retries
  delay: number = 2000 // Increased initial delay to 2 seconds
): Promise<T> => {
  let lastError: Error;
  
  for (let attempt = 1; attempt <= maxRetries + 1; attempt++) {
    try {
      return await requestFn();
    } catch (error) {
      lastError = error as Error;
      
      if (attempt <= maxRetries) {
        console.log(`🔄 Retry attempt ${attempt}/${maxRetries} after ${delay}ms`);
        await new Promise(resolve => setTimeout(resolve, delay));
        delay *= 2; // Exponential backoff
      }
    }
  }
  
  throw lastError!;
};

// API Service Functions
export const apiService = {
  // Test connection to backend
  async healthCheck(): Promise<HealthResponse> {
    return retryRequest(async () => {
      const response = await apiClient.get<HealthResponse>('/health');
      return response.data;
    });
  },
  // Send message to ChatAgent with retry
  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    return retryRequest(async () => {
      const response = await apiClient.post<ChatResponse>('/chat', request);
      return response.data;
    }, 3); // Increased from 1 to 3 retries for chat messages
  },

  // Get API info
  async getApiInfo(): Promise<any> {
    const response = await apiClient.get('/');
    return response.data;
  },

  // Get agents status
  async getAgentsStatus(): Promise<any> {
    const response = await apiClient.get('/agents/status');
    return response.data;
  },
  // Clear conversation memory
  async clearMemory(): Promise<any> {
    const response = await apiClient.delete('/memory/clear');
    return response.data;
  },

  // Get available products (trigger OrderAgent to fetch products)
  async getProducts(): Promise<ProductFromAPI[]> {
    return retryRequest(async () => {
      const chatResponse = await this.sendMessage({
        message: "What products do you have available?",
        session_id: `product_fetch_${Date.now()}`
      });
      
      // Parse products from the agent response
      const products = this.parseProductsFromResponse(chatResponse.response);
      return products;
    });
  },

  // Parse products from agent response text
  parseProductsFromResponse(responseText: string): ProductFromAPI[] {
    const products: ProductFromAPI[] = [];
    
    // Look for the bullet-point format from the backend logs
    const productLines = responseText.match(/• ([^(]+) \(([^)]+)\) - (\$[\d.]+) - ([^\n]+)/g);
    
    if (productLines) {
      productLines.forEach(line => {
        const match = line.match(/• ([^(]+) \(([^)]+)\) - (\$[\d.]+) - ([^\n]+)/);
        if (match) {
          const [, name, sku, price, description] = match;
          products.push({
            sku: sku.trim(),
            name: name.trim(),
            description: description.trim(),
            price: price.trim(),
            category: this.categorizeProduct(name, description)
          });
        }
      });
    }
    
    return products;
  },

  // Helper to categorize products
  categorizeProduct(name: string, description: string): string {
    const text = (name + ' ' + description).toLowerCase();
    if (text.includes('shoe') || text.includes('footwear')) return 'Footwear';
    if (text.includes('shirt') || text.includes('apparel') || text.includes('clothing')) return 'Apparel';
    if (text.includes('hat') || text.includes('cap') || text.includes('accessories')) return 'Accessories';
    if (text.includes('sock')) return 'Apparel';
    return 'General';
  },

  // Get conversation context
  async getConversationContext(sessionId: string): Promise<any> {
    const response = await apiClient.get(`/memory/context/${sessionId}`);
    return response.data;
  },
};

export default apiService;
