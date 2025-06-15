import React, { useState } from 'react';
import { useCart } from '../../contexts/CartContext';
import { Trash2, Plus, Minus, ShoppingBag, X } from 'lucide-react';
import Checkout from './Checkout';

const ShoppingCart: React.FC = () => {
  const { cart, updateQuantity, removeFromCart, clearCart, toggleCart } = useCart();
  const [isCheckoutOpen, setIsCheckoutOpen] = useState(false);

  if (!cart.isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div 
        className="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
        onClick={toggleCart}
      />
      
      {/* Cart Sidebar */}
      <div className="fixed right-0 top-0 h-full w-full max-w-md bg-white shadow-2xl z-50 transform transition-transform duration-300 ease-out">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-secondary-200 bg-gradient-to-r from-primary-50 to-primary-100">
          <div className="flex items-center space-x-3">
            <div className="p-2 bg-primary-500 rounded-xl">
              <ShoppingBag className="w-5 h-5 text-white" />
            </div>
            <div>
              <h2 className="text-xl font-bold text-secondary-800">Shopping Cart</h2>
              <p className="text-sm text-secondary-600">
                {cart.itemCount === 0 
                  ? 'Your cart is empty' 
                  : `${cart.itemCount} item${cart.itemCount > 1 ? 's' : ''}`
                }
              </p>
            </div>
          </div>
          <button
            onClick={toggleCart}
            className="p-2 hover:bg-secondary-100 rounded-xl transition-colors duration-200"
          >
            <X className="w-5 h-5 text-secondary-600" />
          </button>
        </div>

        {/* Cart Items */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4 max-h-[calc(100vh-200px)]">
          {cart.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center">
              <div className="p-4 bg-secondary-100 rounded-full mb-4">
                <ShoppingBag className="w-8 h-8 text-secondary-400" />
              </div>
              <h3 className="text-lg font-semibold text-secondary-800 mb-2">Your cart is empty</h3>
              <p className="text-secondary-600 mb-6">Start shopping to add items to your cart</p>
              <button
                onClick={toggleCart}
                className="btn-primary"
              >
                Continue Shopping
              </button>
            </div>
          ) : (
            cart.items.map((item) => (
              <div
                key={item.id}
                className="card p-4 hover:shadow-medium transition-all duration-200 animate-fade-in"
              >
                <div className="flex items-start space-x-4">
                  {/* Product Image */}
                  <div className="w-16 h-16 bg-gradient-to-br from-primary-100 to-primary-200 rounded-xl flex items-center justify-center flex-shrink-0">
                    {item.image ? (
                      <img 
                        src={item.image} 
                        alt={item.name}
                        className="w-full h-full object-cover rounded-xl"
                      />
                    ) : (
                      <ShoppingBag className="w-6 h-6 text-primary-600" />
                    )}
                  </div>

                  {/* Product Details */}
                  <div className="flex-1 min-w-0">
                    <h3 className="font-semibold text-secondary-800 truncate">{item.name}</h3>
                    {item.description && (
                      <p className="text-sm text-secondary-600 mt-1 line-clamp-2">{item.description}</p>
                    )}
                    <div className="flex items-center justify-between mt-3">
                      <span className="text-lg font-bold text-primary-600">
                        ${(item.price * item.quantity).toFixed(2)}
                      </span>
                      <div className="flex items-center space-x-2">
                        {/* Quantity Controls */}
                        <div className="flex items-center bg-secondary-100 rounded-xl">
                          <button
                            onClick={() => updateQuantity(item.id, item.quantity - 1)}
                            className="p-2 hover:bg-secondary-200 rounded-l-xl transition-colors duration-200"
                          >
                            <Minus className="w-4 h-4 text-secondary-600" />
                          </button>
                          <span className="px-3 py-2 font-semibold text-secondary-800">
                            {item.quantity}
                          </span>
                          <button
                            onClick={() => updateQuantity(item.id, item.quantity + 1)}
                            className="p-2 hover:bg-secondary-200 rounded-r-xl transition-colors duration-200"
                          >
                            <Plus className="w-4 h-4 text-secondary-600" />
                          </button>
                        </div>

                        {/* Remove Button */}
                        <button
                          onClick={() => removeFromCart(item.id)}
                          className="p-2 text-red-500 hover:bg-red-50 rounded-xl transition-colors duration-200"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Footer */}
        {cart.items.length > 0 && (
          <div className="border-t border-secondary-200 p-6 bg-secondary-50">
            <div className="space-y-4">
              {/* Total */}
              <div className="flex items-center justify-between">
                <span className="text-lg font-semibold text-secondary-800">Total</span>
                <span className="text-2xl font-bold text-primary-600">
                  ${cart.total.toFixed(2)}
                </span>
              </div>

              {/* Action Buttons */}
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={clearCart}
                  className="btn-secondary"
                >
                  Clear Cart
                </button>                <button
                  onClick={() => setIsCheckoutOpen(true)}
                  className="btn-primary"
                >
                  Checkout
                </button>
              </div>
            </div>          </div>
        )}
      </div>
      
      {/* Checkout Modal */}
      <Checkout 
        isOpen={isCheckoutOpen} 
        onClose={() => setIsCheckoutOpen(false)} 
      />
    </>
  );
};

export default ShoppingCart;
