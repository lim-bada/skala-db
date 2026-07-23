-- 학사관리시스템 샘플 데이터
-- PostgreSQL용 DML
-- 전제: DDL 실행 직후 모든 테이블이 비어 있고 ID 시퀀스가 1부터 시작한다.
-- 실행 순서: departments -> students/professors/courses/classrooms
--          -> advisors/course_offerings -> enrollments

BEGIN;

-- 1. 학과: 12건
INSERT INTO departments (code, name, office_phone) VALUES
('CSE',    '컴퓨터공학과',       '02-1000-1001'),
('AI',     '인공지능학과',       '02-1000-1002'),
('EE',     '전자공학과',         '02-1000-1003'),
('ME',     '기계공학과',         '02-1000-1004'),
('BA',     '경영학과',           '02-1000-1005'),
('ECON',   '경제학과',           '02-1000-1006'),
('DESIGN', '디자인학과',         '02-1000-1007'),
('BIO',    '생명과학과',         '02-1000-1008'),
('MATH',   '수학과',             '02-1000-1009'),
('KOR',    '국어국문학과',       '02-1000-1010'),
('STAT',   '통계학과',           '02-1000-1011'),
('MEDIA',  '미디어커뮤니케이션학과', '02-1000-1012');

-- 2. 학생: 15건
INSERT INTO students
    (student_no, department_id, name, email, phone, birth_date,
     year_level, status, admission_date)
VALUES
('20230001', 1,  '김민준', 'minjun.kim@univ.ac.kr',   '010-1000-0001', DATE '2004-03-12', 3, 'ENROLLED',  DATE '2023-03-02'),
('20230002', 1,  '이서연', 'seoyeon.lee@univ.ac.kr',  '010-1000-0002', DATE '2004-07-21', 3, 'ENROLLED',  DATE '2023-03-02'),
('20240001', 2,  '박지훈', 'jihoon.park@univ.ac.kr',  '010-1000-0003', DATE '2005-01-08', 2, 'ENROLLED',  DATE '2024-03-04'),
('20240002', 2,  '최유진', 'yujin.choi@univ.ac.kr',   '010-1000-0004', DATE '2005-11-16', 2, 'ENROLLED',  DATE '2024-03-04'),
('20250001', 3,  '정도윤', 'doyun.jeong@univ.ac.kr',  '010-1000-0005', DATE '2006-05-03', 1, 'ENROLLED',  DATE '2025-03-04'),
('20250002', 4,  '한지민', 'jimin.han@univ.ac.kr',    '010-1000-0006', DATE '2006-09-27', 1, 'ENROLLED',  DATE '2025-03-04'),
('20220001', 5,  '윤서준', 'seojun.yoon@univ.ac.kr',  '010-1000-0007', DATE '2003-02-18', 4, 'ENROLLED',  DATE '2022-03-02'),
('20230003', 6,  '강수빈', 'subin.kang@univ.ac.kr',   '010-1000-0008', DATE '2004-08-30', 3, 'LEAVE',     DATE '2023-03-02'),
('20240003', 7,  '조현우', 'hyunwoo.jo@univ.ac.kr',  '010-1000-0009', DATE '2005-04-11', 2, 'ENROLLED',  DATE '2024-03-04'),
('20250003', 8,  '임하은', 'haeun.lim@univ.ac.kr',   '010-1000-0010', DATE '2006-12-05', 1, 'ENROLLED',  DATE '2025-03-04'),
('20220002', 9,  '오지우', 'jiwoo.oh@univ.ac.kr',     '010-1000-0011', DATE '2003-06-14', 4, 'ENROLLED',  DATE '2022-03-02'),
('20210001', 10, '송예린', 'yerin.song@univ.ac.kr',  '010-1000-0012', DATE '2002-10-22', 4, 'GRADUATED', DATE '2021-03-02'),
('20240004', 10, '김채원', 'chaewon.kim@univ.ac.kr', '010-1000-0013', DATE '2005-03-19', 2, 'ENROLLED',  DATE '2024-03-04'),
('20250004', 11, '백승민', 'seungmin.baek@univ.ac.kr','010-1000-0014', DATE '2006-07-07', 1, 'ENROLLED',  DATE '2025-03-04'),
('20230004', 12, '문소희', 'sohee.moon@univ.ac.kr',  '010-1000-0015', DATE '2004-11-02', 3, 'ENROLLED',  DATE '2023-03-02');

-- 3. 교수: 12건
INSERT INTO professors
    (professor_no, department_id, name, email, phone, hire_date)
VALUES
('P001', 1,  '김도현', 'dohyun.kim@univ.ac.kr',   '02-2000-0001', DATE '2014-03-01'),
('P002', 2,  '이수진', 'sujin.lee@univ.ac.kr',    '02-2000-0002', DATE '2018-09-01'),
('P003', 3,  '박성호', 'sungho.park@univ.ac.kr',  '02-2000-0003', DATE '2012-03-01'),
('P004', 4,  '최은영', 'eunyoung.choi@univ.ac.kr','02-2000-0004', DATE '2016-03-01'),
('P005', 5,  '정태훈', 'taehoon.jeong@univ.ac.kr','02-2000-0005', DATE '2010-09-01'),
('P006', 6,  '한미경', 'mikyung.han@univ.ac.kr',  '02-2000-0006', DATE '2015-03-01'),
('P007', 7,  '윤재원', 'jaewon.yoon@univ.ac.kr',  '02-2000-0007', DATE '2019-03-01'),
('P008', 8,  '강지현', 'jihyun.kang@univ.ac.kr',  '02-2000-0008', DATE '2013-09-01'),
('P009', 9,  '조민석', 'minseok.jo@univ.ac.kr',   '02-2000-0009', DATE '2011-03-01'),
('P010', 10, '임선영', 'sunyoung.lim@univ.ac.kr', '02-2000-0010', DATE '2017-03-01'),
('P011', 11, '백준호', 'junho.baek@univ.ac.kr',    '02-2000-0011', DATE '2020-03-01'),
('P012', 12, '문가영', 'gayoung.moon@univ.ac.kr', '02-2000-0012', DATE '2021-09-01');

-- 4. 지도교수: 14건
INSERT INTO advisors (student_id, professor_id, assigned_at) VALUES
(1,  1, DATE '2023-03-02'),
(2,  1, DATE '2023-03-02'),
(3,  2, DATE '2024-03-04'),
(4,  2, DATE '2024-03-04'),
(5,  3, DATE '2025-03-04'),
(6,  4, DATE '2025-03-04'),
(7,  5, DATE '2022-03-02'),
(8,  6, DATE '2023-03-02'),
(9,  7, DATE '2024-03-04'),
(10, 8,  DATE '2025-03-04'),
(11, 9,  DATE '2022-03-02'),
(13, 10, DATE '2024-03-04'),
(14, 11, DATE '2025-03-04'),
(15, 12, DATE '2023-03-02');

-- 5. 교과목: 15건
INSERT INTO courses (course_code, department_id, name, credits, description) VALUES
('CSE101',  1,  '프로그래밍 기초',       3, 'Python을 활용한 프로그래밍 입문'),
('CSE201',  1,  '자료구조',              3, '선형 및 비선형 자료구조'),
('CSE301',  1,  '데이터베이스',          3, '관계형 데이터베이스와 SQL'),
('AI101',   2,  '인공지능 개론',         3, '인공지능의 기본 개념과 활용'),
('AI201',   2,  '머신러닝',              3, '지도학습과 비지도학습'),
('EE101',   3,  '회로이론',              3, '전기회로의 기본 법칙'),
('ME101',   4,  '공학역학',              3, '정역학과 동역학의 기초'),
('BA101',   5,  '경영학 원론',           3, '기업 경영의 기본 원리'),
('ECON101', 6,  '경제학 원론',           3, '미시경제와 거시경제 입문'),
('DES101',  7,  '디자인 기초',           2, '시각 디자인의 기본 원리'),
('BIO101',  8,  '일반생물학',            3, '생명과학의 기본 개념'),
('MATH101', 9,  '대학수학',              3, '미적분과 선형대수 기초'),
('KOR101',  10, '현대문학의 이해',       3, '현대문학 작품의 분석과 감상'),
('STAT101', 11, '기초통계학',            3, '확률과 통계의 기본 개념'),
('MED101',  12, '미디어의 이해',         3, '현대 미디어와 커뮤니케이션');

-- 6. 강의실: 12건
INSERT INTO classrooms (building, room_no, capacity) VALUES
('공학관',   '101', 40),
('공학관',   '201', 50),
('공학관',   '301', 35),
('AI관',     '101', 40),
('AI관',     '202', 30),
('경영관',   '105', 60),
('인문관',   '203', 45),
('자연관',   '101', 50),
('자연관',   '302', 35),
('디자인관', '201', 25),
('인문관',   '305', 35),
('미디어관', '101', 40);

-- 7. 개설강좌: 15건
INSERT INTO course_offerings
    (course_id, professor_id, classroom_id, academic_year, semester,
     section_no, capacity, schedule_info)
VALUES
(1,  1,  1, 2026, 1, 1, 35, '월 09:00-11:50'),
(2,  1,  2, 2026, 1, 1, 40, '화 13:00-15:50'),
(3,  1,  3, 2026, 1, 1, 30, '수 09:00-11:50'),
(4,  2,  4, 2026, 1, 1, 35, '목 13:00-15:50'),
(5,  2,  5, 2026, 1, 1, 25, '금 09:00-11:50'),
(6,  3,  2, 2026, 1, 1, 40, '월 13:00-15:50'),
(7,  4,  1, 2026, 1, 1, 35, '화 09:00-11:50'),
(8,  5,  6, 2026, 1, 1, 50, '수 13:00-15:50'),
(9,  6,  6, 2026, 1, 1, 50, '목 09:00-11:50'),
(10, 7, 10, 2026, 1, 1, 20, '금 13:00-15:50'),
(11, 8,  8, 2026, 2, 1, 40, '월 10:00-12:50'),
(12, 9,  9, 2026, 2, 1, 30, '수 14:00-16:50'),
(13, 10, 11, 2026, 1, 1, 30, '화 10:00-12:50'),
(14, 11,  9, 2026, 2, 1, 30, '목 10:00-12:50'),
(15, 12, 12, 2026, 2, 1, 35, '금 14:00-16:50');

-- 8. 수강신청: 45건
INSERT INTO enrollments
    (student_id, offering_id, enrolled_at, status, score)
VALUES
(1,  1,  DATE '2026-02-16', 'COMPLETED', 96.00),
(1,  2,  DATE '2026-02-16', 'COMPLETED', 88.00),
(1,  11, DATE '2026-07-20', 'ENROLLED',  NULL),
(2,  1,  DATE '2026-02-16', 'COMPLETED', 82.00),
(2,  3,  DATE '2026-02-17', 'COMPLETED', 91.50),
(2,  11, DATE '2026-07-20', 'ENROLLED',  NULL),
(3,  3,  DATE '2026-02-17', 'COMPLETED', 78.00),
(3,  4,  DATE '2026-02-16', 'COMPLETED', 94.00),
(3,  5,  DATE '2026-02-18', 'COMPLETED', 87.50),
(4,  1,  DATE '2026-02-16', 'COMPLETED', 73.00),
(4,  4,  DATE '2026-02-16', 'COMPLETED', 89.00),
(4,  5,  DATE '2026-02-18', 'COMPLETED', 92.00),
(5,  2,  DATE '2026-02-16', 'COMPLETED', 85.00),
(5,  6,  DATE '2026-02-17', 'COMPLETED', 81.00),
(5,  12, DATE '2026-07-21', 'ENROLLED',  NULL),
(6,  3,  DATE '2026-02-17', 'COMPLETED', 68.00),
(6,  7,  DATE '2026-02-16', 'COMPLETED', 90.00),
(6,  12, DATE '2026-07-21', 'ENROLLED',  NULL),
(7,  3,  DATE '2026-02-16', 'COMPLETED', 95.00),
(7,  8,  DATE '2026-02-16', 'COMPLETED', 86.00),
(7,  9,  DATE '2026-02-17', 'CANCELLED', NULL),
(9,  1,  DATE '2026-02-16', 'COMPLETED', 79.00),
(9,  4,  DATE '2026-02-17', 'COMPLETED', 84.50),
(9,  10, DATE '2026-02-16', 'COMPLETED', 93.00),
(10, 5,  DATE '2026-02-17', 'COMPLETED', 77.00),
(10, 11, DATE '2026-07-20', 'ENROLLED',  NULL),
(11, 2,  DATE '2026-02-16', 'COMPLETED', 98.00),
(11, 3,  DATE '2026-02-16', 'COMPLETED', 97.00),
(11, 12, DATE '2026-07-21', 'ENROLLED',  NULL),
(12, 10, DATE '2026-02-16', 'COMPLETED', 88.50),
(1,  13, DATE '2026-02-18', 'COMPLETED', 90.00),
(2,  14, DATE '2026-07-20', 'ENROLLED',  NULL),
(3,  15, DATE '2026-07-21', 'ENROLLED',  NULL),
(4,  13, DATE '2026-02-18', 'COMPLETED', 85.00),
(5,  14, DATE '2026-07-20', 'ENROLLED',  NULL),
(6,  15, DATE '2026-07-21', 'ENROLLED',  NULL),
(7,  13, DATE '2026-02-18', 'COMPLETED', 92.50),
(9,  14, DATE '2026-07-20', 'ENROLLED',  NULL),
(10, 15, DATE '2026-07-21', 'ENROLLED',  NULL),
(11, 13, DATE '2026-02-18', 'COMPLETED', 87.00),
(13, 1,  DATE '2026-02-16', 'COMPLETED', 81.50),
(13, 13, DATE '2026-02-18', 'COMPLETED', 94.00),
(14, 3,  DATE '2026-02-17', 'COMPLETED', 89.50),
(14, 14, DATE '2026-07-20', 'ENROLLED',  NULL),
(15, 15, DATE '2026-07-21', 'ENROLLED',  NULL);

COMMIT;

-- 입력 건수 확인
SELECT 'departments' AS table_name, COUNT(*) AS row_count FROM departments
UNION ALL SELECT 'students',         COUNT(*) FROM students
UNION ALL SELECT 'professors',       COUNT(*) FROM professors
UNION ALL SELECT 'advisors',         COUNT(*) FROM advisors
UNION ALL SELECT 'courses',          COUNT(*) FROM courses
UNION ALL SELECT 'classrooms',       COUNT(*) FROM classrooms
UNION ALL SELECT 'course_offerings', COUNT(*) FROM course_offerings
UNION ALL SELECT 'enrollments',      COUNT(*) FROM enrollments
ORDER BY table_name;
