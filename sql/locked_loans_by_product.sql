-- Locked loans for a given agency product, most recent lock first.
-- Bind params: product (str), start_date (date), row_limit (int)
SELECT loan_id,
       note_rate,
       upb,
       lock_date,
       product
FROM   secondary.locks
WHERE  product = %(product)s
  AND  lock_date >= %(start_date)s
ORDER  BY lock_date DESC
LIMIT  %(row_limit)s;
