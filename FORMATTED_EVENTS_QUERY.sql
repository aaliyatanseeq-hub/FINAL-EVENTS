-- Formatted Events Query for pgAdmin
-- This query formats the events data to look like the frontend display

SELECT 
    event_name AS "Event Name",
    exact_date AS "Date",
    exact_venue AS "Venue",
    category AS "Category",
    ROUND(confidence_score * 100) || '%' AS "Confidence",
    ROUND(hype_score * 100) || '%' AS "Hype Score",
    source_url AS "Source URL",
    created_at AS "Added Date"
FROM events
ORDER BY created_at DESC;

-- Alternative: More detailed format
SELECT 
    event_name AS "Event Name",
    exact_date AS "Date",
    exact_venue AS "Venue",
    location AS "Location",
    category AS "Category",
    ROUND(confidence_score * 100) || '%' AS "Confidence %",
    ROUND(hype_score * 100) || '%' AS "Hype %",
    source_url AS "Link"
FROM events
WHERE event_name != 'Test Event'  -- Exclude test data
ORDER BY exact_date, event_name;

