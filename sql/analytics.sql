-- SQL examples for the SQLite warehouse created by build_warehouse.py.
-- Execute each statement separately against warehouse.db.

-- 1. Product and category performance with a dimension join.
SELECT
    p.product,
    p.category,
    SUM(f.quantity) AS units_sold,
    ROUND(SUM(f.revenue), 2) AS total_revenue
FROM fact_sales AS f
JOIN dim_product AS p ON p.product_key = f.product_key
GROUP BY p.product, p.category
ORDER BY total_revenue DESC;

-- 2. Monthly sales by region: CTE and dimension joins.
WITH monthly_sales AS (
    SELECT d.year, d.month, r.region, SUM(f.revenue) AS revenue
    FROM fact_sales AS f
    JOIN dim_date AS d ON d.date_key = f.date_key
    JOIN dim_region AS r ON r.region_key = f.region_key
    GROUP BY d.year, d.month, r.region
)
SELECT year, month, region, ROUND(revenue, 2) AS revenue
FROM monthly_sales
ORDER BY year, month, revenue DESC;

-- 3. Regional revenue ranking: CTE and window function.
WITH regional_sales AS (
    SELECT r.region, SUM(f.revenue) AS revenue
    FROM fact_sales AS f
    JOIN dim_region AS r ON r.region_key = f.region_key
    GROUP BY r.region
)
SELECT
    region,
    ROUND(revenue, 2) AS revenue,
    DENSE_RANK() OVER (ORDER BY revenue DESC) AS revenue_rank
FROM regional_sales
ORDER BY revenue_rank, region;

-- 4. Category share of total revenue.
WITH category_revenue AS (
    SELECT p.category, SUM(f.revenue) AS revenue
    FROM fact_sales AS f
    JOIN dim_product AS p ON p.product_key = f.product_key
    GROUP BY p.category
)
SELECT
    category,
    ROUND(revenue, 2) AS revenue,
    ROUND(100.0 * revenue / SUM(revenue) OVER (), 2) AS revenue_share_pct
FROM category_revenue
ORDER BY revenue DESC;

-- 5. Inspect a query plan (indexes must be benchmarked, not assumed faster).
EXPLAIN QUERY PLAN
SELECT SUM(f.revenue)
FROM fact_sales AS f
WHERE f.date_key BETWEEN 20240101 AND 20240331;
