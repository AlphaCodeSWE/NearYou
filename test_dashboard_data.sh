#!/bin/bash
echo "🔍 Verifica Rapida Dashboard Analytics Avanzata"
echo "================================================"

echo ""
echo "1. 📊 Conversion Rate %:"
docker exec clickhouse-server clickhouse-client --query "
SELECT ROUND(countIf(offer_accepted = 1) / count() * 100, 1) as conversion_rate 
FROM nearyou.user_visits 
WHERE visit_start_time >= now() - INTERVAL 1 DAY
"

echo ""
echo "2. ⏰ Permanenza Media (ultimi 7 giorni):"
docker exec clickhouse-server clickhouse-client --query "
SELECT ROUND(AVG(duration_minutes), 1) as avg_duration 
FROM nearyou.user_visits 
WHERE visit_start_time >= now() - INTERVAL 7 DAY
"

echo ""
echo "3. 🏪 Top 3 Negozi Revenue (7 giorni):"
docker exec clickhouse-server clickhouse-client --query "
SELECT 
    shop_name,
    COUNT(*) as visite,
    ROUND(SUM(estimated_spending), 2) as revenue,
    ROUND(AVG(duration_minutes), 1) as durata_media,
    ROUND(countIf(offer_accepted = 1) / count() * 100, 1) as conversion_rate
FROM nearyou.user_visits 
WHERE visit_start_time >= now() - INTERVAL 7 DAY
GROUP BY shop_name
ORDER BY revenue DESC
LIMIT 3
"

echo ""
echo "4. 🏷️ Revenue per Categoria (7 giorni):"
docker exec clickhouse-server clickhouse-client --query "
SELECT 
    shop_category,
    ROUND(SUM(estimated_spending), 2) as revenue
FROM nearyou.user_visits 
WHERE visit_start_time >= now() - INTERVAL 7 DAY
GROUP BY shop_category
ORDER BY revenue DESC
LIMIT 5
"

echo ""
echo "5. 📈 Trend Orario Visite (sample):"
docker exec clickhouse-server clickhouse-client --query "
SELECT
    hour_of_day,
    COUNT(*) as visite,
    ROUND(SUM(estimated_spending), 2) as revenue
FROM nearyou.user_visits
WHERE visit_start_time >= now() - INTERVAL 7 DAY
GROUP BY hour_of_day
ORDER BY hour_of_day
LIMIT 5
"

echo ""
echo "6. 💰 Conversione per Livello Sconto (sample):"
docker exec clickhouse-server clickhouse-client --query "
SELECT 
    CASE 
        WHEN (user_satisfaction * 10) < 100 THEN '< 10%'
        WHEN (user_satisfaction * 10) < 200 THEN '10-19%'
        WHEN (user_satisfaction * 10) < 300 THEN '20-29%'
        WHEN (user_satisfaction * 10) < 400 THEN '30-39%'
        ELSE '40%+'
    END as sconto_range,
    ROUND(countIf(offer_accepted = 1) / count() * 100, 1) as conversion_rate,
    COUNT(*) as total_visits
FROM nearyou.user_visits
WHERE visit_start_time >= now() - INTERVAL 7 DAY
GROUP BY sconto_range
ORDER BY sconto_range
LIMIT 3
"

echo ""
echo "✅ Verifiche completate!"
echo ""
echo "🌐 Il dashboard dovrebbe ora mostrare dati reali su:"
echo "   http://localhost:3000"
echo ""
echo "📝 Username: admin | Password: admin"
echo "📈 Cerca: 'NearYou - Dashboard Completa' o 'Dashboard Analytics Avanzata'"
