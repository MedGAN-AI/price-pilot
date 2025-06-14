import React from 'react';
import ProductCard from '../products/ProductCard';
import type { Product } from '../../types/cart';

interface ProductGridProps {
  products: Product[];
  title?: string;
  className?: string;
}

const ProductGrid: React.FC<ProductGridProps> = ({ 
  products, 
  title = "Recommended Products",
  className = ""
}) => {
  if (products.length === 0) return null;

  return (
    <div className={`mt-4 ${className}`}>
      <h3 className="text-lg font-semibold text-secondary-800 mb-4 flex items-center">
        <span className="mr-2">🛍️</span>
        {title}
      </h3>
      
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {products.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            className="animate-fade-in"
          />
        ))}
      </div>
      
      <div className="mt-4 p-3 bg-primary-50 rounded-xl border border-primary-200">
        <p className="text-sm text-primary-700 text-center">
          💡 Click "Add to Cart" on any product to start shopping!
        </p>
      </div>
    </div>
  );
};

export default ProductGrid;
