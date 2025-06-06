-- Create the missing inventory update function for OrderAgent
-- This function safely updates inventory quantities with atomic operations

CREATE OR REPLACE FUNCTION public.update_inventory_stock(
    p_product_id UUID,
    p_adjustment INTEGER,
    p_timestamp TIMESTAMPTZ DEFAULT NOW()
)
RETURNS VOID
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
BEGIN
    -- Update inventory with the adjustment (positive or negative)
    UPDATE inventory 
    SET 
        quantity_in_stock = quantity_in_stock + p_adjustment,
        last_adjusted = p_timestamp,
        updated_at = p_timestamp
    WHERE product_id = p_product_id;
    
    -- If no inventory record exists, create one (for new products)
    IF NOT FOUND THEN
        INSERT INTO inventory (
            id,
            product_id,
            quantity_in_stock,
            last_adjusted,
            updated_at
        ) VALUES (
            gen_random_uuid(),
            p_product_id,
            GREATEST(0, p_adjustment), -- Don't allow negative initial stock
            p_timestamp,
            p_timestamp
        );
    END IF;
    
    -- Ensure stock doesn't go below zero
    UPDATE inventory 
    SET quantity_in_stock = 0 
    WHERE product_id = p_product_id AND quantity_in_stock < 0;
    
END;
$$;

-- Grant execute permission to authenticated users
GRANT EXECUTE ON FUNCTION public.update_inventory_stock TO authenticated;
GRANT EXECUTE ON FUNCTION public.update_inventory_stock TO anon;
