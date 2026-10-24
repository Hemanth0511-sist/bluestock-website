-- Query 1
SELECT COUNT(*) FROM companies;

-- Query 2
SELECT COUNT(*) FROM balancesheet;

-- Query 3
SELECT COUNT(*) FROM profitandloss;

-- Query 4
SELECT company_name
FROM companies
ORDER BY RANDOM()
LIMIT 5;

-- Query 5
SELECT COUNT(*)
FROM companies
WHERE website IS NULL;

-- Query 6
SELECT COUNT(*)
FROM stock_prices;

-- Query 7
SELECT COUNT(DISTINCT company_id)
FROM balancesheet;

-- Query 8
SELECT AVG(roe_percentage)
FROM companies;

-- Query 9
SELECT MAX(market_cap_crore)
FROM market_cap;

-- Query 10
SELECT company_name
FROM companies
WHERE roe_percentage > 20;