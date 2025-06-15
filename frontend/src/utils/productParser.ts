import type { Product } from '../types/cart';
import type { ProductFromAPI } from '../services/api';
import { getProductImage } from './productImages';

/**
 * Converts backend product format to frontend cart format
 */
export const convertAPIProductToCartProduct = (apiProduct: ProductFromAPI): Product => {
  // Parse price from string format like "$79.99"
  const priceNumber = parseFloat(apiProduct.price.replace('$', ''));
  
  return {
    id: apiProduct.sku,
    name: apiProduct.name,
    price: priceNumber,
    description: apiProduct.description,
    category: apiProduct.category,
    availability: 'in_stock', // Default to in stock for backend products
    rating: 4.0 + Math.random() * 1.0, // Random rating between 4-5
    reviews: Math.floor(Math.random() * 500) + 50, // Random reviews
    image: getProductImage(apiProduct.sku, apiProduct.name, apiProduct.category),
  };
};

/**
 * Extracts product information from AI response text
 */
export const extractProductsFromResponse = (responseText: string): Product[] => {
  const products: Product[] = [];
  
  // Look for the structured bullet-point format from OrderAgent
  const productLines = responseText.match(/• ([^(]+) \(([^)]+)\) - (\$[\d.]+) - ([^\n]+)/g);
  
  if (productLines) {
    productLines.forEach(line => {
      const match = line.match(/• ([^(]+) \(([^)]+)\) - (\$[\d.]+) - ([^\n]+)/);
      if (match) {
        const [, name, sku, price, description] = match;
        const priceNumber = parseFloat(price.replace('$', ''));
          if (name && sku && priceNumber > 0) {
          products.push({
            id: sku.trim(),
            name: name.trim(),
            price: priceNumber,
            description: description.trim(),
            category: categorizeProduct(name, description),
            availability: 'in_stock',
            rating: 4.0 + Math.random() * 1.0,
            reviews: Math.floor(Math.random() * 500) + 50,
            image: getProductImage(sku.trim(), name.trim(), categorizeProduct(name, description)),
          });
        }
      }
    });
  }
  
  // Fallback: Look for simple product-price patterns
  if (products.length === 0) {
    const simplePattern = /([A-Z][a-zA-Z\s]+)\s*[-–]\s*\$(\d+\.?\d*)/g;
    let match;
    
    while ((match = simplePattern.exec(responseText)) !== null) {
      const [, name, priceStr] = match;
      const price = parseFloat(priceStr);
      
      if (name && price > 0) {
        products.push({
          id: `product_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          name: name.trim(),
          price: price,
          description: `${name.trim()} - Available now`,
          category: 'General',
          availability: 'in_stock',
          rating: 4.0 + Math.random() * 1.0,
          reviews: Math.floor(Math.random() * 100) + 10,
        });
      }
    }
  }
  
  return products;
};

/**
 * Helper to categorize products based on name and description
 */
const categorizeProduct = (name: string, description: string): string => {
  const text = (name + ' ' + description).toLowerCase();
  if (text.includes('shoe') || text.includes('footwear')) return 'Footwear';
  if (text.includes('shirt') || text.includes('apparel') || text.includes('clothing')) return 'Apparel';
  if (text.includes('hat') || text.includes('cap') || text.includes('accessories')) return 'Accessories';
  if (text.includes('sock')) return 'Apparel';
  return 'General';
};

// Function to create sample products for demo purposes
export const createSampleProducts = (): Product[] => {
  return [
    {
      id: 'sample_1',
      name: 'Wireless Bluetooth Headphones',
      price: 79.99,
      description: 'Premium wireless headphones with noise cancellation',
      category: 'Electronics',
      availability: 'in_stock',
      rating: 4.5,
      reviews: 1234,
    },
    {
      id: 'sample_2',
      name: 'Smart Fitness Tracker',
      price: 129.99,
      description: 'Track your health and fitness with this advanced smartwatch',
      category: 'Health & Fitness',
      availability: 'in_stock',
      rating: 4.2,
      reviews: 856,
    },
    {
      id: 'sample_3',
      name: 'Portable Phone Charger',
      price: 29.99,
      description: '10000mAh power bank with fast charging',
      category: 'Electronics',
      availability: 'low_stock',
      rating: 4.0,
      reviews: 432,
    },
    {
      id: 'sample_4',
      name: 'Premium Coffee Beans',
      price: 19.99,
      description: 'Single-origin coffee beans from Colombia',
      category: 'Food & Beverage',
      availability: 'in_stock',
      rating: 4.8,
      reviews: 967,
    },
    {
      id: 'sample_5',
      name: 'Gaming Mouse',
      price: 49.99,
      description: 'High-precision gaming mouse with RGB lighting',
      category: 'Electronics',
      availability: 'out_of_stock',
      rating: 4.3,
      reviews: 678,
    },
  ];
};
