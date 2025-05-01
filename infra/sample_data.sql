-- Sample data for PricePilot development and testing

-- Sample products
INSERT INTO products (sku, name, description, category, base_cost, current_price, min_price, max_price)
VALUES
    ('TSHIRT-001', 'Premium Cotton T-Shirt', 'High quality 100% cotton t-shirt', 'Apparel', 8.50, 19.99, 14.99, 24.99),
    ('HOODIE-001', 'Zip-up Hoodie', 'Comfortable zip-up hoodie with kangaroo pocket', 'Apparel', 18.75, 39.99, 29.99, 49.99),
    ('JEANS-001', 'Classic Fit Jeans', 'Classic fit blue denim jeans', 'Apparel', 22.50, 49.99, 39.99, 59.99),
    ('PHONE-CASE-001', 'Protective Phone Case', 'Durable phone case with shock absorption', 'Electronics', 5.25, 14.99, 9.99, 19.99),
    ('HEADPHONE-001', 'Wireless Headphones', 'Noise cancelling wireless headphones', 'Electronics', 45.00, 89.99, 69.99, 119.99),
    ('SPEAKER-001', 'Bluetooth Speaker', 'Portable bluetooth speaker with 10-hour battery', 'Electronics', 35.00, 79.99, 59.99, 99.99),
    ('COFFEE-001', 'Premium Coffee Beans', 'Ethically sourced premium coffee beans, 500g', 'Food', 7.50, 14.99, 12.99, 17.99),
    ('TEA-001', 'Organic Green Tea', 'Organic green tea, 50 bags', 'Food', 3.25, 8.99, 6.99, 10.99),
    ('CHOC-001', 'Dark Chocolate Bar', 'Organic 70% dark chocolate bar, 100g', 'Food', 2.00, 4.99, 3.99, 5.99),
    ('CREAM-001', 'Facial Moisturizer', 'Hydrating facial moisturizer, 100ml', 'Beauty', 8.75, 24.99, 19.99, 29.99);

-- Sample sales data (last 60 days)
DO $$
DECLARE
    product_record RECORD;
    sale_date DATE;
    quantity INT;
    price DECIMAL(10, 2);
    total_revenue DECIMAL(10, 2);
BEGIN
    -- Loop through each product
    FOR product_record IN SELECT id, current_price FROM products LOOP
        -- Generate sales for the last 60 days
        FOR i IN 1..60 LOOP
            sale_date := CURRENT_DATE - (i || ' days')::INTERVAL;
            
            -- Generate random quantity (with some weekend boost and randomness)
            IF EXTRACT(DOW FROM sale_date) IN (0, 6) THEN -- Weekend
                quantity := FLOOR(RANDOM() * 10) + 5; -- 5-15 units
            ELSE
                quantity := FLOOR(RANDOM() * 8) + 2; -- 2-10 units
            END IF;
            
            -- Add some randomness to the price (occasional discounts)
            IF RANDOM() < 0.1 THEN -- 10% chance of discount
                price := ROUND(product_record.current_price * 0.9, 2); -- 10% discount
            ELSE
                price := product_record.current_price;
            END IF;
            
            -- Calculate revenue
            total_revenue := price * quantity;
            
            -- Insert sale record
            INSERT INTO sales (product_id, date, quantity, price, total_revenue)
            VALUES (product_record.id, sale_date, quantity, price, total_revenue);
        END LOOP;
    END LOOP;
END $$;

-- Sample competitor prices
INSERT INTO competitor_prices (product_id, competitor_name, price, url, timestamp)
VALUES
    (1, 'CompetitorA', 18.99, 'https://competitora.example.com/product1', CURRENT_TIMESTAMP - INTERVAL '5 days'),
    (1, 'CompetitorB', 21.99, 'https://competitorb.example.com/product1', CURRENT_TIMESTAMP - INTERVAL '3 days'),
    (1, 'CompetitorC', 20.49, 'https://competitorc.example.com/product1', CURRENT_TIMESTAMP - INTERVAL '1 day'),
    (2, 'CompetitorA', 37.99, 'https://competitora.example.com/product2', CURRENT_TIMESTAMP - INTERVAL '5 days'),
    (2, 'CompetitorB', 42.99, 'https://competitorb.example.com/product2', CURRENT_TIMESTAMP - INTERVAL '3 days'),
    (3, 'CompetitorA', 47.99, 'https://competitora.example.com/product3', CURRENT_TIMESTAMP - INTERVAL '4 days'),
    (3, 'CompetitorB', 52.99, 'https://competitorb.example.com/product3', CURRENT_TIMESTAMP - INTERVAL '2 days'),
    (4, 'CompetitorA', 13.99, 'https://competitora.example.com/product4', CURRENT_TIMESTAMP - INTERVAL '6 days'),
    (4, 'CompetitorC', 15.99, 'https://competitorc.example.com/product4', CURRENT_TIMESTAMP - INTERVAL '1 day'),
    (5, 'CompetitorB', 84.99, 'https://competitorb.example.com/product5', CURRENT_TIMESTAMP - INTERVAL '7 days'),
    (5, 'CompetitorC', 94.99, 'https://competitorc.example.com/product5', CURRENT_TIMESTAMP - INTERVAL '2 days');

-- Sample price recommendations
INSERT INTO price_recommendations 
(product_id, current_price, recommended_price, min_price, max_price, confidence_score, 
 estimated_demand, estimated_revenue, estimated_profit, rationale, applied)
VALUES
    (1, 19.99, 21.99, 14.99, 24.99, 0.85, 95.5, 2100.05, 1285.75, 
     'Recommendation is to increase price by 10%. This keeps us below average competitor price of $20.49. Expected demand at this price: 95.5 units. Projected profit: $1285.75', 
     FALSE),
    (2, 39.99, 41.99, 29.99, 49.99, 0.78, 88.2, 3703.52, 2048.24, 
     'Recommendation is to increase price by 5%. Our recommended price is below average competitor price of $40.49. Expected demand at this price: 88.2 units. Projected profit: $2048.24', 
     FALSE),
    (3, 49.99, 52.99, 39.99, 59.99, 0.82, 78.5, 4159.72, 2390.08, 
     'Recommendation is to increase price by 6%. This is in line with competitor price trends. Expected demand at this price: 78.5 units. Projected profit: $2390.08', 
     FALSE),
    (4, 14.99, 13.99, 9.99, 19.99, 0.88, 112.3, 1571.07, 978.05, 
     'Recommendation is to decrease price by 6.7%. This positions us competitively in the market. Expected demand at this price: 112.3 units. Projected profit: $978.05', 
     TRUE),
    (5, 89.99, 94.99, 69.99, 119.99, 0.75, 65.8, 6250.34, 3284.84, 
     'Recommendation is to increase price by 5.6%. This aligns with the higher end of the market for premium products. Expected demand at this price: 65.8 units. Projected profit: $3284.84', 
     FALSE);

-- Sample price changes
INSERT INTO price_changes (product_id, old_price, new_price, changed_by, rationale, recommendation_id)
VALUES
    (4, 14.99, 13.99, 'system', 'Automated price update based on recommendation', 4);