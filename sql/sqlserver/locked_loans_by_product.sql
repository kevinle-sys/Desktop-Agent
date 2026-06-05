-- SQL Server (T-SQL) version of locked loans by product, newest lock first.
-- Bind params (:name style): row_limit (int), product (str), start_date (date)
-- Note: T-SQL uses TOP instead of LIMIT, and :name binds instead of %(name)s.
SELECT TOP (:row_limit)
       loan_id,
       note_rate,
       upb,
       lock_date,
       product
FROM   dbo.locks
WHERE  product = :product
  AND  lock_date >= :start_date
ORDER  BY lock_date DESC;
