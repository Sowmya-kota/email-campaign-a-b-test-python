USE marketing_analytics;

-- Analysis-ready layer. The raw table is never modified.
CREATE OR REPLACE VIEW email_test_clean AS
SELECT
    customer_id,
    CASE segment
        WHEN 'Mens E-Mail'   THEN 'Mens'
        WHEN 'Womens E-Mail' THEN 'Womens'
        WHEN 'No E-Mail'     THEN 'Control'
    END AS test_group,

    -- pre-campaign customer profile
    recency,
    CASE
        WHEN recency <= 3 THEN '01-03 months'
        WHEN recency <= 6 THEN '04-06 months'
        WHEN recency <= 9 THEN '07-09 months'
        ELSE                   '10-12 months'
    END AS recency_band,
    history,
    history_segment,
    CASE
        WHEN mens = 1 AND womens = 1 THEN 'Both'
        WHEN mens = 1                THEN 'Mens only'
        ELSE                              'Womens only'
    END AS past_purchase,
    CASE zip_code WHEN 'Surburban' THEN 'Suburban' ELSE zip_code END AS area,  -- fixes source typo
    CASE newbie WHEN 1 THEN 'New' ELSE 'Existing' END AS customer_type,
    channel,

    -- outcomes (2-week window)
    visit,
    conversion,
    spend
FROM email_test_raw;
