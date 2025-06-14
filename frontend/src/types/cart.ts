// Shopping Cart Types
export interface CartItem {
  id: string;
  name: string;
  price: number;
  quantity: number;
  image?: string;
  description?: string;
  category?: string;
  availability?: 'in_stock' | 'low_stock' | 'out_of_stock';
}

export interface CartState {
  items: CartItem[];
  total: number;
  itemCount: number;
  isOpen: boolean;
}

export interface CartContextType {
  cart: CartState;
  addToCart: (item: Omit<CartItem, 'quantity'>, quantity?: number) => void;
  removeFromCart: (itemId: string) => void;
  updateQuantity: (itemId: string, quantity: number) => void;
  clearCart: () => void;
  toggleCart: () => void;
  getItemQuantity: (itemId: string) => number;
}

export interface Product {
  id: string;
  name: string;
  price: number;
  description: string;
  image?: string;
  category: string;
  availability: 'in_stock' | 'low_stock' | 'out_of_stock';
  rating?: number;
  reviews?: number;
}
