-- Aggregate open pipeline UPB and weighted-average note rate by coupon.
-- Bind params: as_of_date (date), row_limit (int)
SELECT product,
       coupon,
       COUNT(*)                                   AS loan_count,
       SUM(upb)                                   AS total_upb,
       SUM(upb * note_rate) / NULLIF(SUM(upb), 0) AS wac
FROM   secondary.pipeline
WHERE  status = 'OPEN'
  AND  as_of_date = %(as_of_date)s
GROUP  BY product, coupon
ORDER  BY product, coupon
LIMIT  %(row_limit)s;
