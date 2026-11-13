USE marketing_analytics;

-- 1. Rule checks: every value should be 0
SELECT 'duplicate customer_id' AS check_name,
       COUNT(*) - COUNT(DISTINCT customer_id) AS failed_rows
FROM email_test_raw
UNION ALL
SELECT 'recency outside 1-12', COUNT(*) FROM email_test_raw WHERE recency NOT BETWEEN 1 AND 12
UNION ALL
SELECT 'history <= 0', COUNT(*) FROM email_test_raw WHERE history <= 0
UNION ALL
SELECT 'spend < 0', COUNT(*) FROM email_test_raw WHERE spend < 0
UNION ALL
SELECT 'flag not 0/1', COUNT(*) FROM email_test_raw
WHERE mens NOT IN (0, 1) OR womens NOT IN (0, 1) OR newbie NOT IN (0, 1)
   OR visit NOT IN (0, 1) OR conversion NOT IN (0, 1)
UNION ALL
SELECT 'converted without visiting', COUNT(*) FROM email_test_raw WHERE conversion = 1 AND visit = 0
UNION ALL
SELECT 'spend > 0 but not converted', COUNT(*) FROM email_test_raw WHERE spend > 0 AND conversion = 0
UNION ALL
SELECT 'converted but spend = 0', COUNT(*) FROM email_test_raw WHERE conversion = 1 AND spend = 0
UNION ALL
SELECT 'bought neither mens nor womens', COUNT(*) FROM email_test_raw WHERE mens = 0 AND womens = 0;

-- 2. Allowed values: are categories clean?
SELECT 'segment' AS column_name, segment AS value, COUNT(*) AS customers FROM email_test_raw GROUP BY segment
UNION ALL
SELECT 'zip_code', zip_code, COUNT(*) FROM email_test_raw GROUP BY zip_code
UNION ALL
SELECT 'channel', channel, COUNT(*) FROM email_test_raw GROUP BY channel
UNION ALL
SELECT 'history_segment', history_segment, COUNT(*) FROM email_test_raw GROUP BY history_segment
ORDER BY column_name, value;

-- 3. Does history_segment match the history amount?
SELECT history_segment,
       MIN(history) AS min_history,
       MAX(history) AS max_history,
       COUNT(*)     AS customers
FROM email_test_raw
GROUP BY history_segment
ORDER BY history_segment;
