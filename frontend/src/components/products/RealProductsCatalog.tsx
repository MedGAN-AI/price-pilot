import React, { useState, useEffect } from 'react';
import { apiService } from '../../services/api';
import { convertAPIProductToCartProduct } from '../../utils/productParser';
import ProductGrid from '../products/ProductGrid';
import LoadingSpinner from '../ui/LoadingSpinner';
import ErrorMessage from '../ui/ErrorMessage';
import type { Product } from '../../types/cart';

const RealProductsCatalog: React.FC = () => {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchProducts = async () => {
    setLoading(true);
    setError(null);
    
    try {
      console.log('🛍️ Fetching real products from backend...');
      const apiProducts = await apiService.getProducts();
      
      // Convert API products to cart format
      const cartProducts = apiProducts.map(convertAPIProductToCartProduct);
      setProducts(cartProducts);
      
      console.log('✅ Fetched real products:', cartProducts);
    } catch (err) {
      console.error('❌ Error fetching products:', err);
      setError(err instanceof Error ? err.message : 'Failed to load products');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProducts();
  }, []);

  if (loading) {
    return (
      <div className="card p-6">
        <LoadingSpinner message="Loading real products from backend..." />
      </div>
    );
  }

  if (error) {
    return (
      <div className="card p-6">
        <ErrorMessage 
          message={error}
          onRetry={fetchProducts}
          onDismiss={() => setError(null)}
        />
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="card p-6 text-center">
        <h3 className="text-lg font-semibold text-secondary-800 mb-2">
          No Products Available
        </h3>
        <p className="text-secondary-600 mb-4">
          No products found in the backend. Make sure the backend is running and has product data.
        </p>
        <button
          onClick={fetchProducts}
          className="btn-primary"
        >
          Retry Loading
        </button>
      </div>
    );
  }

  return (
    <div className="animate-fade-in">
      <div className="mb-6">
        <h2 className="text-2xl font-bold text-secondary-800 mb-2">
          🛍️ Available Products
        </h2>
        <p className="text-secondary-600">
          Real products from our backend inventory system
        </p>
      </div>
      
      <ProductGrid 
        products={products}
        title={`${products.length} Products Available`}
      />
      
      <div className="mt-6 p-4 bg-blue-50 rounded-xl border border-blue-200">
        <p className="text-blue-700 text-sm text-center">
          💡 These are real products from the backend. Add them to your cart and test the shopping experience!
        </p>
      </div>
    </div>
  );
};

export default RealProductsCatalog;
