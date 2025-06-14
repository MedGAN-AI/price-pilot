import React from 'react';
import { useCart } from '../../contexts/CartContext';
import { ShoppingBag } from 'lucide-react';

const CartButton: React.FC = () => {
  const { cart, toggleCart } = useCart();

  return (
    <button
      onClick={toggleCart}
      className="relative p-3 bg-white/90 backdrop-blur-sm hover:bg-white border border-secondary-200 rounded-xl shadow-soft hover:shadow-medium transition-all duration-200 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2"
    >
      <ShoppingBag className="w-6 h-6 text-secondary-700" />
      
      {/* Item Count Badge */}
      {cart.itemCount > 0 && (
        <div className="absolute -top-2 -right-2 bg-primary-500 text-white text-xs font-bold rounded-full w-5 h-5 flex items-center justify-center animate-bounce-subtle">
          {cart.itemCount > 99 ? '99+' : cart.itemCount}
        </div>
      )}
    </button>
  );
};

export default CartButton;
