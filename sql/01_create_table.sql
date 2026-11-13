-- Raw data exactly as received: one row per customer
CREATE DATABASE IF NOT EXISTS marketing_analytics;
USE marketing_analytics;

CREATE TABLE IF NOT EXISTS email_test_raw (
    customer_id      INT           NOT NULL PRIMARY KEY,
    recency          TINYINT       NOT NULL,  -- months since last purchase
    history_segment  VARCHAR(20)   NOT NULL,
    history          DECIMAL(10,2) NOT NULL,  -- dollars spent in past 12 months
    mens             TINYINT       NOT NULL,  -- bought men's items (1/0)
    womens           TINYINT       NOT NULL,  -- bought women's items (1/0)
    zip_code         VARCHAR(20)   NOT NULL,
    newbie           TINYINT       NOT NULL,  -- new customer in last 12 months (1/0)
    channel          VARCHAR(20)   NOT NULL,
    segment          VARCHAR(20)   NOT NULL,  -- experiment group
    visit            TINYINT       NOT NULL,  -- visited in 2-week window (1/0)
    conversion       TINYINT       NOT NULL,  -- purchased in 2-week window (1/0)
    spend            DECIMAL(10,2) NOT NULL   -- dollars spent in 2-week window
);
