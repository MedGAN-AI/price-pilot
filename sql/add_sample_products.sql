-- Add sample products and inventory for OrderAgent testing
-- This will ensure the agent has products to work with

-- Insert sample products
INSERT INTO products (id, sku, name, description, price, category, created_at, updated_at) 
VALUES 
    ('eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 'HAT-GRN-005', 'Green Baseball Cap', 'Comfortable green baseball cap with adjustable strap', 24.99, 'Accessories', NOW(), NOW()),
    ('ffffffff-ffff-ffff-ffff-ffffffffffff', 'HAT-BLU-001', 'Blue Baseball Cap', 'Classic blue baseball cap, one size fits all', 22.99, 'Accessories', NOW(), NOW()),
    ('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'SHIRT-RED-M', 'Red T-Shirt Medium', 'Cotton red t-shirt in medium size', 19.99, 'Clothing', NOW(), NOW()),
    ('bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'SHIRT-BLU-L', 'Blue T-Shirt Large', 'Cotton blue t-shirt in large size', 19.99, 'Clothing', NOW(), NOW()),
    ('cccccccc-cccc-cccc-cccc-cccccccccccc', 'JACKET-BLK-M', 'Black Jacket Medium', 'Water-resistant black jacket in medium', 89.99, 'Outerwear', NOW(), NOW())
ON CONFLICT (sku) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description,
    price = EXCLUDED.price,
    category = EXCLUDED.category,
    updated_at = NOW();

-- Insert corresponding inventory records
INSERT INTO inventory (id, product_id, quantity_in_stock, last_adjusted, updated_at)
VALUES 
    (gen_random_uuid(), 'eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee', 50, NOW(), NOW()),
    (gen_random_uuid(), 'ffffffff-ffff-ffff-ffff-ffffffffffff', 25, NOW(), NOW()),
    (gen_random_uuid(), 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 30, NOW(), NOW()),
    (gen_random_uuid(), 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 40, NOW(), NOW()),
    (gen_random_uuid(), 'cccccccc-cccc-cccc-cccc-cccccccccccc', 15, NOW(), NOW())
ON CONFLICT (product_id) DO UPDATE SET
    quantity_in_stock = EXCLUDED.quantity_in_stock,
    last_adjusted = EXCLUDED.last_adjusted,
    updated_at = NOW();
