-- 종합실습2 실행계획 성능 비교
-- 대상 DB: skala_db
-- search_path: lab, public
--
-- EXPLAIN ANALYZE는 실제로 쿼리를 실행한다.
-- 아래 쿼리는 모두 SELECT이므로 데이터를 변경하지 않는다.

BEGIN READ ONLY;

-- ============================================================
-- 비교 1. 미수강 학생 조회: NOT IN vs NOT EXISTS
-- 두 쿼리는 student_id와 name을 동일하게 반환한다.
-- NOT IN의 NULL 문제를 피하기 위해 서브쿼리에서 NULL을 제외한다.
-- ============================================================

-- 1-1. NOT IN + hashed SubPlan
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    s.student_id,
    s.name
FROM student AS s
WHERE s.student_id NOT IN (
    SELECT e.student_id
    FROM enroll AS e
    WHERE e.student_id IS NOT NULL
)
ORDER BY s.student_id;

-- 1-2. NOT EXISTS + Anti Join
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    s.student_id,
    s.name
FROM student AS s
WHERE NOT EXISTS (
    SELECT 1
    FROM enroll AS e
    WHERE e.student_id = s.student_id
)
ORDER BY s.student_id;

-- ============================================================
-- 비교 2. 학과 평균보다 GPA가 높은 학생:
-- 상관 서브쿼리 vs 학과 평균 사전 집계 JOIN
-- 두 쿼리는 동일한 495명을 반환한다.
-- ============================================================

-- 2-1. 상관 서브쿼리
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT
    s.student_id,
    s.name,
    s.major,
    s.gpa
FROM student AS s
WHERE s.gpa > (
    SELECT AVG(s2.gpa)
    FROM student AS s2
    WHERE s2.major = s.major
)
ORDER BY
    s.major,
    s.gpa DESC,
    s.student_id;

-- 2-2. 학과 평균을 한 번만 계산하는 CTE + JOIN
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
WITH major_avg AS (
    SELECT
        major,
        AVG(gpa) AS avg_gpa
    FROM student
    GROUP BY major
)
SELECT
    s.student_id,
    s.name,
    s.major,
    s.gpa
FROM student AS s
INNER JOIN major_avg AS a
    ON a.major = s.major
WHERE s.gpa > a.avg_gpa
ORDER BY
    s.major,
    s.gpa DESC,
    s.student_id;

COMMIT;
