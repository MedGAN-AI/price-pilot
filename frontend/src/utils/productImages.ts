/**
 * Product Image Mapping Utility
 * Maps product SKUs to appropriate images using Unsplash or placeholder images
 */

interface ProductImageMap {
  [key: string]: string;
}

// Mapping of product categories to Unsplash search terms
const categoryImageMap: { [key: string]: string } = {
  'footwear': 'shoes',
  'apparel': 'clothing',
  'accessories': 'accessories',
  'general': 'product'
};

// Specific product SKU to image mapping
const productImageMap: ProductImageMap = {
  // Shoes
  'SHOES-RED-001': 'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop&crop=center', // Red Running Shoes
  'SHOES-BLU-002': 'https://images.unsplash.com/photo-1551107696-a4b0c5a0d9a2?w=400&h=400&fit=crop&crop=center', // Blue Trail Shoes
  
  // Apparel
  'TSHIRT-WHT-003': 'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop&crop=center', // White Cotton T-Shirt
  'TSHIRT-BLK-004': 'https://images.unsplash.com/photo-1503341338650-664e2d2f9bb0?w=400&h=400&fit=crop&crop=center', // Black Cotton T-Shirt
  
  // Accessories
  'HAT-GRN-005': 'https://images.unsplash.com/photo-1531984232640-5d2d7ff860e6?w=400&h=400&fit=crop&crop=center', // Green Baseball Cap
  'SOCKS-MLT-006': 'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&h=400&fit=crop&crop=center', // Multicolor Athletic Socks
};

/**
 * Get image URL for a product based on SKU, name, or category
 */
export const getProductImage = (
  sku?: string, 
  name?: string, 
  category?: string
): string => {
  // First try to get image by SKU
  if (sku && productImageMap[sku]) {
    return productImageMap[sku];
  }
  
  // If no specific SKU mapping, generate based on product name/category
  if (name || category) {
    const searchTerm = getSearchTermFromProduct(name, category);
    return generateUnsplashUrl(searchTerm);
  }
  
  // Default fallback image
  return generateUnsplashUrl('product');
};

/**
 * Generate search term from product name and category
 */
const getSearchTermFromProduct = (name?: string, category?: string): string => {
  const nameStr = name?.toLowerCase() || '';
  const categoryStr = category?.toLowerCase() || '';
  
  // Check for specific product types in name
  if (nameStr.includes('shoe') || nameStr.includes('sneaker') || nameStr.includes('boot')) {
    return 'shoes';
  }
  if (nameStr.includes('shirt') || nameStr.includes('tee') || nameStr.includes('top')) {
    return 'tshirt';
  }
  if (nameStr.includes('cap') || nameStr.includes('hat')) {
    return 'cap';
  }
  if (nameStr.includes('sock')) {
    return 'socks';
  }
  if (nameStr.includes('jacket') || nameStr.includes('coat')) {
    return 'jacket';
  }
  if (nameStr.includes('pants') || nameStr.includes('jeans')) {
    return 'pants';
  }
  
  // Fall back to category mapping
  return categoryImageMap[categoryStr] || 'product';
};

/**
 * Generate Unsplash URL with consistent parameters
 */
const generateUnsplashUrl = (searchTerm: string): string => {
  const baseUrl = 'https://images.unsplash.com/photo-';
  const params = 'w=400&h=400&fit=crop&crop=center&auto=format&q=80';
  
  // Use a consistent set of photo IDs for each search term
  const photoIds: { [key: string]: string } = {
    'shoes': '1542291026-7eec264c27ff',
    'tshirt': '1521572163474-6864f9cf17ab',
    'cap': '1531984232640-5d2d7ff860e6',
    'socks': '1584464491033-06628f3a6b7b',
    'jacket': '1544966503-7ad5ac882d5d',
    'pants': '1594633312681-b6127da51aad',
    'clothing': '1445205170444-8fcb136c9813',
    'accessories': '1515562141207-7a88fb7ce338',
    'product': '1560472354-b33ff0c44a43'
  };
  
  const photoId = photoIds[searchTerm] || photoIds['product'];
  return `${baseUrl}${photoId}?${params}`;
};

/**
 * Preload product images for better performance
 */
export const preloadProductImages = (products: Array<{ sku?: string; name?: string; category?: string }>) => {
  products.forEach(product => {
    const imageUrl = getProductImage(product.sku, product.name, product.category);
    const img = new Image();
    img.src = imageUrl;
  });
};

/**
 * Get a set of default product images for placeholders
 */
export const getDefaultProductImages = (): string[] => {
  return [
    'https://images.unsplash.com/photo-1542291026-7eec264c27ff?w=400&h=400&fit=crop&crop=center&auto=format&q=80',
    'https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=400&h=400&fit=crop&crop=center&auto=format&q=80',
    'https://images.unsplash.com/photo-1531984232640-5d2d7ff860e6?w=400&h=400&fit=crop&crop=center&auto=format&q=80',
    'https://images.unsplash.com/photo-1584464491033-06628f3a6b7b?w=400&h=400&fit=crop&crop=center&auto=format&q=80',
  ];
};
