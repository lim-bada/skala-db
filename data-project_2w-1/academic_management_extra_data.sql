-- 학사관리시스템 추가 샘플 데이터
-- academic_management_sample_data.sql 실행 후 사용한다.
-- ON CONFLICT DO NOTHING으로 동일 파일을 다시 실행해도 중복 행을 건너뛴다.

BEGIN;

-- 학생 5건 추가: 총 20건
INSERT INTO students
    (student_no, department_id, name, email, phone, birth_date,
     year_level, status, admission_date)
VALUES
('20250005', (SELECT id FROM departments WHERE code = 'CSE'),
 '김태윤', 'taeyun.kim@univ.ac.kr', '010-1000-0016', DATE '2006-01-17',
 1, 'ENROLLED', DATE '2025-03-04'),
('20240005', (SELECT id FROM departments WHERE code = 'AI'),
 '신나연', 'nayeon.shin@univ.ac.kr', '010-1000-0017', DATE '2005-08-09',
 2, 'ENROLLED', DATE '2024-03-04'),
('20230005', (SELECT id FROM departments WHERE code = 'BA'),
 '서준혁', 'junhyuk.seo@univ.ac.kr', '010-1000-0018', DATE '2004-04-25',
 3, 'ENROLLED', DATE '2023-03-02'),
('20250006', (SELECT id FROM departments WHERE code = 'STAT'),
 '권다은', 'daeun.kwon@univ.ac.kr', '010-1000-0019', DATE '2006-10-13',
 1, 'ENROLLED', DATE '2025-03-04'),
('20240006', (SELECT id FROM departments WHERE code = 'MEDIA'),
 '홍민재', 'minjae.hong@univ.ac.kr', '010-1000-0020', DATE '2005-12-01',
 2, 'ENROLLED', DATE '2024-03-04')
ON CONFLICT (student_no) DO NOTHING;

-- 교수 3건 추가: 총 15건
INSERT INTO professors
    (professor_no, department_id, name, email, phone, hire_date)
VALUES
('P013', (SELECT id FROM departments WHERE code = 'CSE'),
 '오세훈', 'sehoon.oh@univ.ac.kr', '02-2000-0013', DATE '2022-03-01'),
('P014', (SELECT id FROM departments WHERE code = 'AI'),
 '류지영', 'jiyoung.ryu@univ.ac.kr', '02-2000-0014', DATE '2023-03-01'),
('P015', (SELECT id FROM departments WHERE code = 'MEDIA'),
 '서동욱', 'dongwook.seo@univ.ac.kr', '02-2000-0015', DATE '2021-03-01')
ON CONFLICT (professor_no) DO NOTHING;

-- 지도교수 관계 5건 추가: 총 19건
INSERT INTO advisors (student_id, professor_id, assigned_at) VALUES
((SELECT id FROM students WHERE student_no = '20250005'),
 (SELECT id FROM professors WHERE professor_no = 'P013'), DATE '2025-03-04'),
((SELECT id FROM students WHERE student_no = '20240005'),
 (SELECT id FROM professors WHERE professor_no = 'P014'), DATE '2024-03-04'),
((SELECT id FROM students WHERE student_no = '20230005'),
 (SELECT id FROM professors WHERE professor_no = 'P005'), DATE '2023-03-02'),
((SELECT id FROM students WHERE student_no = '20250006'),
 (SELECT id FROM professors WHERE professor_no = 'P011'), DATE '2025-03-04'),
((SELECT id FROM students WHERE student_no = '20240006'),
 (SELECT id FROM professors WHERE professor_no = 'P015'), DATE '2024-03-04')
ON CONFLICT (student_id) DO NOTHING;

-- 교과목 5건 추가: 총 20건
INSERT INTO courses (course_code, department_id, name, credits, description) VALUES
('CSE401', (SELECT id FROM departments WHERE code = 'CSE'),
 '클라우드 컴퓨팅', 3, '클라우드 인프라와 서비스 구성'),
('CSE402', (SELECT id FROM departments WHERE code = 'CSE'),
 '정보보안', 3, '정보보호 원리와 네트워크 보안'),
('AI301', (SELECT id FROM departments WHERE code = 'AI'),
 '딥러닝', 3, '신경망과 딥러닝 모델의 이해'),
('STAT201', (SELECT id FROM departments WHERE code = 'STAT'),
 '데이터분석', 3, '통계 기반 데이터 분석 실습'),
('MED201', (SELECT id FROM departments WHERE code = 'MEDIA'),
 '디지털콘텐츠기획', 3, '디지털 미디어 콘텐츠 설계와 기획')
ON CONFLICT (course_code) DO NOTHING;

-- 강의실 3건 추가: 총 15건
INSERT INTO classrooms (building, room_no, capacity) VALUES
('공학관',   '401', 45),
('AI관',     '303', 35),
('미디어관', '202', 30)
ON CONFLICT (building, room_no) DO NOTHING;

-- 개설강좌 5건 추가: 총 20건
INSERT INTO course_offerings
    (course_id, professor_id, classroom_id, academic_year, semester,
     section_no, capacity, schedule_info)
VALUES
((SELECT id FROM courses WHERE course_code = 'CSE401'),
 (SELECT id FROM professors WHERE professor_no = 'P013'),
 (SELECT id FROM classrooms WHERE building = '공학관' AND room_no = '401'),
 2026, 1, 1, 40, '월 14:00-16:50'),
((SELECT id FROM courses WHERE course_code = 'CSE402'),
 (SELECT id FROM professors WHERE professor_no = 'P013'),
 (SELECT id FROM classrooms WHERE building = '공학관' AND room_no = '401'),
 2026, 2, 1, 40, '화 14:00-16:50'),
((SELECT id FROM courses WHERE course_code = 'AI301'),
 (SELECT id FROM professors WHERE professor_no = 'P014'),
 (SELECT id FROM classrooms WHERE building = 'AI관' AND room_no = '303'),
 2026, 1, 1, 30, '수 14:00-16:50'),
((SELECT id FROM courses WHERE course_code = 'STAT201'),
 (SELECT id FROM professors WHERE professor_no = 'P011'),
 (SELECT id FROM classrooms WHERE building = '자연관' AND room_no = '302'),
 2026, 2, 1, 30, '목 14:00-16:50'),
((SELECT id FROM courses WHERE course_code = 'MED201'),
 (SELECT id FROM professors WHERE professor_no = 'P015'),
 (SELECT id FROM classrooms WHERE building = '미디어관' AND room_no = '202'),
 2026, 2, 1, 25, '금 10:00-12:50')
ON CONFLICT (course_id, academic_year, semester, section_no) DO NOTHING;

-- 수강신청 25건 추가: 총 70건
WITH additional_enrollments
    (student_no, course_code, academic_year, semester, section_no,
     enrolled_at, status, score)
AS (
    VALUES
    ('20230001', 'CSE401', 2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 93.00::numeric),
    ('20230002', 'CSE401', 2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 86.50::numeric),
    ('20250005', 'CSE401', 2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 88.00::numeric),
    ('20240005', 'CSE401', 2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 91.00::numeric),
    ('20230005', 'CSE401', 2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 79.50::numeric),

    ('20240001', 'CSE402', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20240002', 'CSE402', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20250005', 'CSE402', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20250006', 'CSE402', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20240006', 'CSE402', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),

    ('20240001', 'AI301',  2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 95.00::numeric),
    ('20240002', 'AI301',  2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 89.00::numeric),
    ('20240005', 'AI301',  2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 97.00::numeric),
    ('20230005', 'AI301',  2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 83.50::numeric),
    ('20240006', 'AI301',  2026, 1, 1, DATE '2026-02-18', 'COMPLETED', 76.00::numeric),

    ('20250001', 'STAT201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20220002', 'STAT201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20250004', 'STAT201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20250006', 'STAT201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20240006', 'STAT201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),

    ('20240003', 'MED201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20240004', 'MED201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20230004', 'MED201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20230005', 'MED201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric),
    ('20240006', 'MED201', 2026, 2, 1, DATE '2026-07-22', 'ENROLLED', NULL::numeric)
)
INSERT INTO enrollments
    (student_id, offering_id, enrolled_at, status, score)
SELECT
    s.id,
    co.id,
    ae.enrolled_at,
    ae.status,
    ae.score
FROM additional_enrollments ae
JOIN students s
  ON s.student_no = ae.student_no
JOIN courses c
  ON c.course_code = ae.course_code
JOIN course_offerings co
  ON co.course_id = c.id
 AND co.academic_year = ae.academic_year
 AND co.semester = ae.semester
 AND co.section_no = ae.section_no
ON CONFLICT (student_id, offering_id) DO NOTHING;

COMMIT;

-- 추가 후 전체 건수 확인
SELECT 'departments' AS table_name, COUNT(*) AS row_count FROM departments
UNION ALL SELECT 'students',         COUNT(*) FROM students
UNION ALL SELECT 'professors',       COUNT(*) FROM professors
UNION ALL SELECT 'advisors',         COUNT(*) FROM advisors
UNION ALL SELECT 'courses',          COUNT(*) FROM courses
UNION ALL SELECT 'classrooms',       COUNT(*) FROM classrooms
UNION ALL SELECT 'course_offerings', COUNT(*) FROM course_offerings
UNION ALL SELECT 'enrollments',      COUNT(*) FROM enrollments
ORDER BY table_name;
