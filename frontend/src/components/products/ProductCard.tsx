import React, { useState } from 'react';
import { useCart } from '../../contexts/CartContext';
import { ShoppingCart, Plus, Star, Package, AlertCircle } from 'lucide-react';
import type { Product } from '../../types/cart';

interface ProductCardProps {
  product: Product;
  className?: string;
}

const ProductCard: React.FC<ProductCardProps> = ({ product, className = '' }) => {
  const { addToCart, getItemQuantity } = useCart();
  const [isAdding, setIsAdding] = useState(false);
  const itemQuantity = getItemQuantity(product.id);

  const handleAddToCart = async () => {
    setIsAdding(true);
    
    // Add to cart
    addToCart({
      id: product.id,
      name: product.name,
      price: product.price,
      image: product.image,
      description: product.description,
      category: product.category,
      availability: product.availability,
    });

    // Add a slight delay for better UX
    setTimeout(() => {
      setIsAdding(false);
    }, 500);
  };

  const getAvailabilityColor = (availability: string) => {
    switch (availability) {
      case 'in_stock':
        return 'text-green-600 bg-green-100';
      case 'low_stock':
        return 'text-yellow-600 bg-yellow-100';
      case 'out_of_stock':
        return 'text-red-600 bg-red-100';
      default:
        return 'text-secondary-600 bg-secondary-100';
    }
  };

  const getAvailabilityText = (availability: string) => {
    switch (availability) {
      case 'in_stock':
        return 'In Stock';
      case 'low_stock':
        return 'Low Stock';
      case 'out_of_stock':
        return 'Out of Stock';
      default:
        return 'Unknown';
    }
  };

  const isOutOfStock = product.availability === 'out_of_stock';

  return (
    <div className={`card p-4 hover:shadow-medium transition-all duration-300 transform hover:scale-[1.02] ${className}`}>
      {/* Product Image */}
      <div className="relative mb-4">
        <div className="w-full h-48 bg-gradient-to-br from-primary-100 to-primary-200 rounded-xl flex items-center justify-center overflow-hidden">
          {product.image ? (
            <img 
              src={product.image} 
              alt={product.name}
              className="w-full h-full object-cover"
            />
          ) : (
            <Package className="w-16 h-16 text-primary-600" />
          )}
        </div>
        
        {/* Availability Badge */}
        <div className={`absolute top-2 right-2 px-2 py-1 rounded-full text-xs font-medium ${getAvailabilityColor(product.availability)}`}>
          {getAvailabilityText(product.availability)}
        </div>

        {/* Quantity Badge */}
        {itemQuantity > 0 && (
          <div className="absolute top-2 left-2 bg-primary-500 text-white px-2 py-1 rounded-full text-xs font-bold">
            {itemQuantity} in cart
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="space-y-3">
        <div>
          <h3 className="font-bold text-lg text-secondary-800 line-clamp-2">{product.name}</h3>
          {product.description && (
            <p className="text-secondary-600 text-sm mt-1 line-clamp-2">{product.description}</p>
          )}
        </div>

        {/* Category */}
        <div className="flex items-center space-x-2">
          <span className="px-2 py-1 bg-secondary-100 text-secondary-700 rounded-lg text-xs font-medium">
            {product.category}
          </span>
        </div>

        {/* Rating */}
        {product.rating && (
          <div className="flex items-center space-x-2">
            <div className="flex items-center">
              {[...Array(5)].map((_, i) => (
                <Star
                  key={i}
                  className={`w-4 h-4 ${
                    i < Math.floor(product.rating!)
                      ? 'text-yellow-400 fill-current'
                      : 'text-secondary-300'
                  }`}
                />
              ))}
            </div>
            <span className="text-sm text-secondary-600">
              {product.rating.toFixed(1)}
              {product.reviews && ` (${product.reviews})`}
            </span>
          </div>
        )}

        {/* Price and Add to Cart */}
        <div className="flex items-center justify-between pt-2 border-t border-secondary-200">
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-primary-600">
              ${product.price.toFixed(2)}
            </span>
          </div>
          
          <button
            onClick={handleAddToCart}
            disabled={isOutOfStock || isAdding}
            className={`flex items-center space-x-2 px-4 py-2 rounded-xl font-medium transition-all duration-200 transform hover:scale-105 focus:outline-none focus:ring-2 focus:ring-offset-2 ${
              isOutOfStock
                ? 'bg-secondary-200 text-secondary-500 cursor-not-allowed'
                : isAdding
                ? 'bg-primary-400 text-white cursor-wait'
                : 'bg-primary-500 hover:bg-primary-600 text-white shadow-medium hover:shadow-lg focus:ring-primary-500'
            }`}
          >
            {isOutOfStock ? (
              <>
                <AlertCircle className="w-4 h-4" />
                <span>Unavailable</span>
              </>
            ) : isAdding ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                <span>Adding...</span>
              </>
            ) : (
              <>
                {itemQuantity > 0 ? (
                  <>
                    <Plus className="w-4 h-4" />
                    <span>Add More</span>
                  </>
                ) : (
                  <>
                    <ShoppingCart className="w-4 h-4" />
                    <span>Add to Cart</span>
                  </>
                )}
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;
