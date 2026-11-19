import json
import logging
import os
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

# Apply links (`apply_url`) point at the official online application portal for
# each exam. They are stable entry-point URLs (or cycle-scoped direct links for
# currently-open notices), researched against official sources on 2026-11-16.
# They must be re-verified each application season exactly like the deadlines
# (see docs/SEED_VERIFICATION_2026-11-15.md). Rows without an apply_url are
# intentionally left blank rather than guessed — the UI hides the Apply button
# for them and only the official notification PDF is shown.

_BASE_SEED_EXAMS = [
    # ==================== 10TH & 12TH PASS GOVERNMENT JOBS ====================
    {
        "id": "ssc-chsl-12th",
        "title": "SSC Combined Higher Secondary Level (CHSL)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Clerical / Intermediate",
        "notification_date": date(2026, 9, 7),
        "application_deadline": date(2026, 10, 7),
        "exam_date": None,
        "official_pdf_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_chsl_2026.pdf",
        "apply_url": "https://ssc.gov.in/home/apply",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 27,
        "age_cutoff_date": date(2026, 8, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["Any", "PCM", "PCB", "Commerce", "Arts"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Percentages", "Ratio & Proportion", "Algebra", "Geometry",
            "Trigonometry", "Coding-Decoding", "Syllogism", "Blood Relations",
            "Reading Comprehension", "Error Spotting", "Active/Passive Voice",
            "Indian Polity", "Modern History", "Current Affairs", "General Science"
        }
    },
    {
        "id": "nda-na-12th",
        "title": "UPSC National Defence Academy & Naval Academy (NDA & NA)",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "Defense / Officer Cadet",
        "notification_date": date(2026, 5, 20),
        "application_deadline": date(2026, 6, 9),
        "exam_date": date(2026, 9, 13),
        "official_pdf_url": "https://www.upsc.gov.in/sites/default/files/Notif-NDA-II-2026-Engl-200526.pdf",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 16,
        "max_age_general": 19,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["PCM (Physics, Chemistry, Maths)", "PCM", "Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Algebra", "Trigonometry", "Matrices & Determinants", "Calculus",
            "Vector Algebra", "Statistics & Probability", "Physics", "Chemistry",
            "General Science", "History & Freedom Movement", "Geography", "Current Affairs", "English Grammar"
        }
    },
    {
        "id": "rrb-ntpc-undergrad-12th",
        "title": "RRB NTPC Undergraduate Posts (Clerk & Typist)",
        "organizing_body": "Railway Recruitment Board (RRB)",
        "post_type": "Railways / Intermediate",
        "notification_date": date(2026, 10, 14),
        "application_deadline": date(2026, 11, 15),
        "exam_date": None,
        "official_pdf_url": "https://rrb.indianrailways.gov.in/",
        "apply_url": "https://rrbapply.gov.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 30,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["Any"],
        "min_percentage": 50.0,
        "state_restriction": None,
        "topics": {
            "Number Systems", "Percentages", "Ratio & Proportion", "Algebra",
            "Data Interpretation", "Syllogism", "Blood Relations", "Coding-Decoding",
            "Indian Polity", "Modern History", "General Science", "Current Affairs"
        }
    },
    {
        "id": "ssc-mts-havaldar-10th",
        "title": "SSC Multi-Tasking Staff (MTS) & Havaldar",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Central Govt / Matriculation",
        "notification_date": date(2025, 6, 26),
        "application_deadline": date(2025, 7, 24),
        "exam_date": None,
        "official_pdf_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_mts_2025.pdf",
        "apply_url": "https://ssc.gov.in/home/apply",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 25,
        "age_cutoff_date": date(2026, 8, 1),
        "allowed_degrees": ["10th", "10th Pass", "Matriculation"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Number Systems", "Percentages", "Ratio & Proportion", "Simple Interest",
            "Coding-Decoding", "Directions", "Analogies", "Reading Comprehension",
            "Synonyms & Antonyms", "General Awareness", "Current Affairs", "General Science"
        }
    },
    {
        "id": "ssc-gd-constable-10th",
        "title": "SSC GD Constable (CAPFs, SSF & Rifleman)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Paramilitary / Police",
        "notification_date": date(2025, 12, 1),
        "application_deadline": date(2025, 12, 31),
        "exam_date": None,
        "official_pdf_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_CTGD_2026.pdf",
        "apply_url": "https://ssc.gov.in/home/apply",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 23,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["10th", "10th Pass", "Matriculation"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Elementary Mathematics", "Percentages", "Ratio & Proportion",
            "Spatial Visualization", "Analogies", "Coding-Decoding",
            "General Knowledge", "Current Affairs", "Basic Hindi / English Comprehension"
        }
    },
    {
        "id": "delhi-police-constable-12th",
        "title": "Delhi Police Executive Constable (Male / Female)",
        "organizing_body": "Staff Selection Commission (SSC) / Delhi Police",
        "post_type": "Law Enforcement / Police",
        "notification_date": date(2025, 9, 22),
        "application_deadline": date(2025, 10, 21),
        "exam_date": None,
        "official_pdf_url": "https://delhipolice.gov.in/RecruitmentFile/63193_NoticeConstable2025.pdf",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 25,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Reasoning", "Number Systems", "Percentages", "Time & Distance",
            "Current Affairs", "Indian History", "Indian Polity", "Basic Computer Knowledge"
        }
    },

    # ==================== GRADUATE & TECHNICAL JOBS ====================
    {
        "id": "ssc-cgl-general",
        "title": "SSC Combined Graduate Level (CGL)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "General Graduate",
        "notification_date": date(2026, 5, 21),
        "application_deadline": date(2026, 6, 22),
        "exam_date": date(2026, 9, 30),
        "official_pdf_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_cgl_2026.pdf",
        "apply_url": "https://ssc.gov.in/home/apply",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 8, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Number Systems", "Percentages", "Ratio & Proportion", "Algebra",
            "Geometry", "Trigonometry", "Data Interpretation", "Syllogism",
            "Blood Relations", "Coding-Decoding", "Reading Comprehension",
            "Error Spotting", "Active/Passive Voice", "Indian Polity",
            "Modern History", "Current Affairs", "Basic Computer Knowledge"
        }
    },
    {
        "id": "rrb-ntpc-grad",
        "title": "RRB NTPC Graduate Posts",
        "organizing_body": "Railway Recruitment Board (RRB)",
        "post_type": "General Graduate",
        "notification_date": date(2026, 10, 7),
        "application_deadline": date(2026, 11, 6),
        "exam_date": None,
        "official_pdf_url": "https://rrb.indianrailways.gov.in/",
        "apply_url": "https://rrbapply.gov.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 33,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Number Systems", "Percentages", "Ratio & Proportion", "Algebra",
            "Geometry", "Trigonometry", "Data Interpretation", "Syllogism",
            "Blood Relations", "Coding-Decoding", "Indian Polity",
            "Modern History", "Current Affairs", "General Science"
        }
    },
    {
        "id": "ibps-so-it-officer",
        "title": "IBPS Specialist Officer (IT Officer Scale-I)",
        "organizing_body": "Institute of Banking Personnel Selection (IBPS)",
        "post_type": "Technical / Specialist",
        "notification_date": date(2026, 6, 30),
        "application_deadline": date(2026, 7, 21),
        "exam_date": date(2026, 8, 29),
        "official_pdf_url": "https://www.ibps.in/wp-content/uploads/Detailed-Notification-CRP-SPL-XVI_Final_V1_30.06.2026.pdf",
        "apply_url": "https://ibpsreg.ibps.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 20,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 11, 1),
        "allowed_degrees": ["B.Tech", "BE", "MCA", "M.Sc", "BCA"],
        "allowed_streams": ["Computer Science", "Information Technology", "Computer Applications", "Electronics"],
        "min_percentage": 50.0,
        "state_restriction": None,
        "topics": {
            "Data Interpretation", "Syllogism", "Coding-Decoding",
            "Reading Comprehension", "Error Spotting", "DBMS & SQL",
            "Data Structures & Algorithms", "Computer Networks",
            "Operating Systems", "Software Engineering", "Web Technologies", "Cyber Security"
        }
    },
    {
        "id": "nic-scientific-technical-asst",
        "title": "NIC / NIELIT Scientific & Technical Assistant-A",
        "organizing_body": "National Informatics Centre (NIC / NIELIT)",
        "post_type": "Technical / Specialist",
        "notification_date": None,
        "application_deadline": date(2026, 9, 30),
        "exam_date": None,
        "official_pdf_url": "https://recruitment.nic.in/DetailedSTA.pdf",
        "apply_url": "https://recruitment.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 12, 20),
        "allowed_degrees": ["B.Tech", "BE", "MCA", "M.Sc", "BCA"],
        "allowed_streams": ["Computer Science", "Information Technology", "Computer Applications", "Electronics"],
        "min_percentage": 60.0,
        "state_restriction": None,
        "topics": {
            "Percentages", "Ratio & Proportion", "Syllogism", "Coding-Decoding",
            "DBMS & SQL", "Data Structures & Algorithms", "Computer Networks",
            "Operating Systems", "Software Engineering", "Web Technologies",
            "Object Oriented Programming", "Digital Logic"
        }
    },
    {
        "id": "sbi-po-general",
        "title": "SBI Probationary Officer (PO)",
        "organizing_body": "State Bank of India (SBI)",
        "post_type": "Banking / Finance",
        "notification_date": date(2026, 6, 18),
        "application_deadline": date(2026, 7, 8),
        "exam_date": None,
        "official_pdf_url": "https://sbi.bank.in/web/careers/current-openings",
        "apply_url": "https://sbi.bank.in/web/careers/current-openings",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 4, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Data Interpretation", "Percentages", "Ratio & Proportion",
            "Syllogism", "Seating Arrangement", "Puzzles", "Blood Relations",
            "Reading Comprehension", "Error Spotting", "Cloze Test",
            "Banking & Financial Awareness", "Current Affairs", "Basic Computer Knowledge"
        }
    },
    {
        "id": "ib-acio-grade-ii",
        "title": "Intelligence Bureau ACIO Grade-II / Executive",
        "organizing_body": "Ministry of Home Affairs (MHA)",
        "post_type": "Defense / Intelligence",
        "notification_date": None,
        "application_deadline": date(2025, 8, 10),
        "exam_date": None,
        "official_pdf_url": "https://www.mha.gov.in/",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 27,
        "age_cutoff_date": date(2026, 12, 18),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Number Systems", "Percentages", "Ratio & Proportion", "Data Interpretation",
            "Syllogism", "Blood Relations", "Coding-Decoding", "Reading Comprehension",
            "Error Spotting", "Indian Polity", "Modern History", "Current Affairs",
            "Internal Security & Geopolitics", "Essay Writing"
        }
    },
    {
        "id": "upsc-cse-ias",
        "title": "UPSC Civil Services Examination (IAS / IPS / IFS)",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "All India Services",
        "notification_date": date(2026, 2, 4),
        "application_deadline": date(2026, 2, 27),
        "exam_date": date(2026, 5, 24),
        "official_pdf_url": "https://www.upsc.gov.in/examinations/Civil%20Services%20%28Preliminary%29%20Examination%2C%202026",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 32,
        "age_cutoff_date": date(2027, 8, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Indian Polity", "Modern History", "Ancient & Medieval History",
            "Physical & Indian Geography", "Indian Economy", "Environment & Ecology",
            "Science & Technology", "Current Affairs", "Ethics, Integrity & Aptitude",
            "Reading Comprehension", "Data Interpretation", "Essay Writing"
        }
    },
    {
        "id": "drdo-scientist-b-cs",
        "title": "DRDO Scientist 'B' (Computer Science & Engineering)",
        "organizing_body": "DRDO Recruitment & Assessment Centre (RAC)",
        "post_type": "Technical / Specialist",
        "notification_date": None,
        "application_deadline": date(2025, 7, 4),
        "exam_date": None,
        "official_pdf_url": "https://rac.gov.in/download/advt_156_v3.pdf",
        "apply_url": "https://rac.gov.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 28,
        "age_cutoff_date": date(2026, 12, 28),
        "allowed_degrees": ["B.Tech", "BE", "M.Tech", "ME"],
        "allowed_streams": ["Computer Science", "Information Technology"],
        "min_percentage": 60.0,
        "state_restriction": None,
        "topics": {
            "Engineering Mathematics", "Digital Logic", "Computer Organization & Architecture",
            "Data Structures & Algorithms", "Operating Systems", "DBMS & SQL",
            "Computer Networks", "Compiler Design", "Theory of Computation", "Software Engineering"
        }
    },

    # ==================== 10TH & 12TH PASS / DIPLOMA JOBS (EXPANDED) ====================
    {
        "id": "ssc-stenographer-12th",
        "title": "SSC Stenographer (Grade C & D)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Clerical / Typing & Shorthand",
        "notification_date": date(2026, 4, 24),
        "application_deadline": date(2026, 5, 15),
        "exam_date": date(2026, 9, 9),
        "official_pdf_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_steno_2026.pdf",
        "apply_url": "https://ssc.gov.in/home/apply",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 27,
        "age_cutoff_date": date(2026, 8, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "English Comprehension", "Error Spotting", "Synonyms & Antonyms",
            "Cloze Test", "Reading Comprehension", "General Awareness",
            "Current Affairs", "Basic Computer Knowledge"
        }
    },
    {
        "id": "indian-army-agniveer-gd",
        "title": "Indian Army Agniveer (General Duty)",
        "organizing_body": "Indian Army",
        "post_type": "Defense / Soldier",
        "notification_date": None,
        "application_deadline": date(2026, 4, 1),
        "exam_date": date(2026, 6, 1),
        "official_pdf_url": "https://joinindianarmy.nic.in/writereaddata/Portal/BRAVO_NotificationPDF/Rally_Ntfn__Men__2027_12_FEB_2026.pdf",
        "apply_url": "https://joinindianarmy.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 17,
        "max_age_general": 21,
        "age_cutoff_date": date(2027, 4, 1),
        "allowed_degrees": ["10th", "10th Pass", "Matriculation", "12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["Any"],
        "min_percentage": 45.0,
        "state_restriction": None,
        "topics": {
            "Basic Mathematics", "General Knowledge", "Indian History",
            "Indian Polity", "General Science", "Logical Reasoning",
            "Current Affairs", "Physical Fitness"
        }
    },
    {
        "id": "iaf-agniveervayu",
        "title": "Indian Air Force Agniveer Vayu (Intake)",
        "organizing_body": "Indian Air Force (IAF)",
        "post_type": "Defense / Agniveervayu",
        "notification_date": None,
        "application_deadline": date(2026, 7, 26),
        "exam_date": date(2026, 9, 22),
        "official_pdf_url": "https://iafrecruitment.edcil.co.in/agniveervayu/pdffiles/Advt%20Agniveervayu%2002%20of%2027.pdf",
        "apply_url": "https://iafrecruitment.edcil.co.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 17,
        "max_age_general": 21,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate", "Diploma"],
        "allowed_streams": ["PCM", "PCM (Physics, Chemistry, Maths)"],
        "min_percentage": 50.0,
        "state_restriction": None,
        "topics": {
            "Physics", "Chemistry", "Mathematics", "English",
            "General Awareness", "Reasoning", "Computer Basics", "Current Affairs"
        }
    },
    {
        "id": "indian-navy-mr",
        "title": "Indian Navy Agniveer (MR – Sailor)",
        "organizing_body": "Indian Navy",
        "post_type": "Defense / Sailor",
        "notification_date": None,
        "application_deadline": date(2026, 4, 6),
        "exam_date": None,
        "official_pdf_url": "https://www.joinindiannavy.gov.in/files/Advt_Agniveer_MR_01_27_and_02_27_English.pdf",
        "apply_url": "https://www.joinindiannavy.gov.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 17,
        "max_age_general": 21,
        "age_cutoff_date": date(2027, 7, 1),
        "allowed_degrees": ["10th", "10th Pass", "Matriculation"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Elementary Mathematics", "General Science", "General Knowledge",
            "English", "Reasoning", "Current Affairs", "Basic Computer Knowledge",
            "Physical Fitness"
        }
    },
    {
        "id": "indian-navy-ssr",
        "title": "Indian Navy Agniveer (SSR – Sailor)",
        "organizing_body": "Indian Navy",
        "post_type": "Defense / Sailor",
        "notification_date": None,
        "application_deadline": date(2026, 4, 6),
        "exam_date": None,
        "official_pdf_url": "https://www.joinindiannavy.gov.in/files/Advt_Agniveer_SSR_01_27_and_02_27_English.pdf",
        "apply_url": "https://www.joinindiannavy.gov.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 17,
        "max_age_general": 21,
        "age_cutoff_date": date(2027, 7, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["PCM", "PCM (Physics, Chemistry, Maths)"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Physics", "Chemistry", "Mathematics", "English",
            "Reasoning", "General Awareness", "Current Affairs", "Computer Basics"
        }
    },
    {
        "id": "indian-army-technical",
        "title": "Indian Army Agniveer (Technical)",
        "organizing_body": "Indian Army",
        "post_type": "Defense / Technical Soldier",
        "notification_date": None,
        "application_deadline": date(2026, 4, 1),
        "exam_date": date(2026, 6, 3),
        "official_pdf_url": "https://www.joinindianarmy.nic.in/writereaddata/Portal/BRAVO_NotificationPDF/ARO_Berhampore__Indian_army_Recruitment_Notification_2027_AV_Male.pdf",
        "apply_url": "https://joinindianarmy.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 17,
        "max_age_general": 23,
        "age_cutoff_date": date(2027, 10, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["PCM", "PCM (Physics, Chemistry, Maths)"],
        "min_percentage": 50.0,
        "state_restriction": None,
        "topics": {
            "Physics", "Chemistry", "Mathematics", "General Knowledge",
            "English", "General Science", "Reasoning", "Current Affairs"
        }
    },
    {
        "id": "rrb-alp-10th",
        "title": "RRB Assistant Loco Pilot (ALP)",
        "organizing_body": "Railway Recruitment Board (RRB)",
        "post_type": "Railways / Technical (ITI)",
        "notification_date": date(2026, 5, 14),
        "application_deadline": date(2026, 6, 14),
        "exam_date": date(2026, 11, 3),
        "official_pdf_url": "https://rrb.indianrailways.gov.in/-/image/1780467818641detail_cen_01_2026_eng.pdf/examsDocuments",
        "apply_url": "https://rrbapply.gov.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 30,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["10th", "10th Pass", "Matriculation", "Diploma"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Number Systems", "Percentages", "Ratio & Proportion", "Algebra",
            "Trigonometry", "Mensuration", "Data Interpretation", "Time & Distance",
            "General Science", "Basic Engineering & Loco Awareness", "Current Affairs", "Logical Reasoning"
        }
    },
    {
        "id": "rrb-je-diploma",
        "title": "RRB Junior Engineer (JE)",
        "organizing_body": "Railway Recruitment Board (RRB)",
        "post_type": "Railways / Technical (Diploma)",
        "notification_date": date(2026, 8, 13),
        "application_deadline": date(2026, 9, 13),
        "exam_date": date(2026, 10, 27),
        "official_pdf_url": "https://rrb.indianrailways.gov.in/-/image/1787058904504CEN_04_2026_JE_DMS_English.pdf/examsDocuments",
        "apply_url": "https://rrbapply.gov.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 33,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Diploma", "B.Tech", "BE"],
        "allowed_streams": ["Mechanical", "Civil", "Electrical", "Electronics"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Engineering Mathematics", "Basic Engineering Mechanics",
            "Electrical Circuits", "Civil Technology", "Workshop Calculations",
            "Data Interpretation", "General Science", "Current Affairs"
        }
    },
    {
        "id": "ssc-je-diploma",
        "title": "SSC Junior Engineer (Civil / Mechanical / Electrical)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Central Govt / Technical (Diploma)",
        "notification_date": date(2026, 9, 2),
        "application_deadline": date(2026, 9, 22),
        "exam_date": date(2026, 11, 2),
        "official_pdf_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_je_2026.pdf",
        "apply_url": "https://ssc.gov.in/home/apply",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 32,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Diploma", "B.Tech", "BE"],
        "allowed_streams": ["Civil", "Mechanical", "Electrical"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Engineering Mathematics", "Structural Mechanics", "RCC Design",
            "Electrical Machines", "Engineering Mechanics", "Data Interpretation",
            "General Awareness", "Current Affairs"
        }
    },
    {
        "id": "rrb-technician-diploma",
        "title": "RRB Technician Grade-I",
        "organizing_body": "Railway Recruitment Board (RRB)",
        "post_type": "Railways / Technical (Diploma)",
        "notification_date": date(2026, 6, 30),
        "application_deadline": date(2026, 7, 29),
        "exam_date": date(2026, 10, 6),
        "official_pdf_url": "https://rrb.indianrailways.gov.in/-/image/1783081193700Detailed_CEN_02_20262.pdf/examsDocuments",
        "apply_url": "https://rrbapply.gov.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 33,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Diploma", "B.Tech", "BE"],
        "allowed_streams": ["Mechanical", "Electrical", "Electronics"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Engineering Drawing", "Workshop Science & Technology",
            "Electrical Machines", "Engineering Mathematics",
            "Data Interpretation", "General Awareness", "Current Affairs"
        }
    },

    # ==================== BANKING & FINANCIAL SERVICES ====================
    {
        "id": "ibps-po-general",
        "title": "IBPS Probationary Officer (PO / Management Trainee)",
        "organizing_body": "Institute of Banking Personnel Selection (IBPS)",
        "post_type": "Banking / Finance",
        "notification_date": date(2026, 7, 1),
        "application_deadline": date(2026, 7, 21),
        "exam_date": date(2026, 8, 22),
        "official_pdf_url": "https://ibps.in/wp-content/uploads/Detailed-Notification_CRP-PO-XVI_Final_V1_30.06.2026.pdf",
        "apply_url": "https://ibpsreg.ibps.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 20,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 10, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Data Interpretation", "Percentages", "Ratio & Proportion",
            "Seating Arrangement", "Puzzles", "Blood Relations",
            "Reading Comprehension", "Error Spotting", "Cloze Test",
            "Banking & Financial Awareness", "Current Affairs", "Basic Computer Knowledge"
        }
    },
    {
        "id": "ibps-clerk-general",
        "title": "IBPS Customer Service Associate (Clerk)",
        "organizing_body": "Institute of Banking Personnel Selection (IBPS)",
        "post_type": "Banking / Finance",
        "notification_date": date(2026, 8, 1),
        "application_deadline": date(2026, 8, 21),
        "exam_date": None,
        "official_pdf_url": "https://ibps.in/wp-content/uploads/Notification_CRP_CSA_XVI-Final.pdf",
        "apply_url": "https://ibpsreg.ibps.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 20,
        "max_age_general": 28,
        "age_cutoff_date": date(2026, 10, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Data Interpretation", "Percentages", "Ratio & Proportion",
            "Seating Arrangement", "Puzzles", "Syllogism",
            "Reading Comprehension", "Error Spotting", "Cloze Test",
            "Banking & Financial Awareness", "Current Affairs", "Basic Computer Knowledge"
        }
    },
    {
        "id": "sbi-clerk-general",
        "title": "SBI Clerk (Junior Associates)",
        "organizing_body": "State Bank of India (SBI)",
        "post_type": "Banking / Finance",
        "notification_date": date(2025, 8, 5),
        "application_deadline": date(2025, 8, 26),
        "exam_date": None,
        "official_pdf_url": "https://sbi.bank.in/documents/77530/52947104/JA+2025+-Detailed+Advt.pdf",
        "apply_url": "https://sbi.bank.in/web/careers/current-openings",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 20,
        "max_age_general": 28,
        "age_cutoff_date": date(2026, 4, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Data Interpretation", "Percentages", "Ratio & Proportion",
            "Seating Arrangement", "Puzzles", "Syllogism",
            "Reading Comprehension", "Error Spotting", "Banking & Financial Awareness",
            "Current Affairs", "Basic Computer Knowledge"
        }
    },
    {
        "id": "ibps-rrb-officer-scale1",
        "title": "IBPS RRB Officer Scale-I (PO equivalent)",
        "organizing_body": "Institute of Banking Personnel Selection (IBPS)",
        "post_type": "Banking / Finance (Regional Rural Banks)",
        "notification_date": date(2026, 9, 1),
        "application_deadline": date(2026, 9, 27),
        "exam_date": date(2026, 11, 21),
        "official_pdf_url": "https://ibps.in/wp-content/uploads/CRP-RRBs-XV-notification_Revised.pdf",
        "apply_url": "https://ibpsreg.ibps.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 11, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Data Interpretation", "Percentages", "Ratio & Proportion",
            "Seating Arrangement", "Puzzles", "Reading Comprehension",
            "Error Spotting", "Banking & Financial Awareness",
            "Current Affairs", "Basic Computer Knowledge"
        }
    },
    {
        "id": "ibps-rrb-clerk",
        "title": "IBPS RRB Office Assistant (Clerk, Multipurpose)",
        "organizing_body": "Institute of Banking Personnel Selection (IBPS)",
        "post_type": "Banking / Finance (Regional Rural Banks)",
        "notification_date": date(2026, 9, 1),
        "application_deadline": date(2026, 9, 27),
        "exam_date": date(2026, 12, 6),
        "official_pdf_url": "https://ibps.in/wp-content/uploads/CRP-RRBs-XV-notification_Revised.pdf",
        "apply_url": "https://ibpsreg.ibps.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 28,
        "age_cutoff_date": date(2026, 11, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Data Interpretation", "Percentages", "Ratio & Proportion",
            "Seating Arrangement", "Puzzles", "Reading Comprehension",
            "Banking & Financial Awareness", "Current Affairs", "Basic Computer Knowledge"
        }
    },
    {
        "id": "rbi-assistant",
        "title": "RBI Assistant",
        "organizing_body": "Reserve Bank of India (RBI)",
        "post_type": "Banking / Finance (Regulator)",
        "notification_date": date(2026, 2, 16),
        "application_deadline": date(2026, 3, 8),
        "exam_date": date(2026, 4, 11),
        "official_pdf_url": "https://rbidocs.rbi.org.in/rdocs/Content/PDFs/DAASSISTANT2025CCB4E54CEB5542D9987FE6D1EA51D143.PDF",
        "apply_url": "https://opportunities.rbi.org.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 28,
        "age_cutoff_date": date(2026, 12, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Data Interpretation", "Syllogism", "Seating Arrangement",
            "Puzzles", "Reading Comprehension", "Error Spotting",
            "Banking & Financial Awareness", "Computer Knowledge",
            "Current Affairs", "Indian Economy"
        }
    },
    {
        "id": "rbi-grade-b",
        "title": "RBI Grade B Officer",
        "organizing_body": "Reserve Bank of India (RBI)",
        "post_type": "Banking / Finance (Regulator)",
        "notification_date": date(2026, 4, 29),
        "application_deadline": date(2026, 5, 20),
        "exam_date": date(2026, 6, 13),
        "official_pdf_url": "https://www.rbi.org.in/Scripts/bs_viewcontent.aspx?Id=4997",
        "apply_url": "https://opportunities.rbi.org.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2027, 2, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Indian Economy", "Budget & Economic Survey",
            "Banking & Financial Awareness", "Constitution & Governance",
            "Ethics", "English Writing", "Quantitative Aptitude",
            "Logical Reasoning", "Current Affairs", "General Awareness"
        }
    },
    {
        "id": "nabard-grade-a",
        "title": "NABARD Grade-A Officer (RDBS)",
        "organizing_body": "National Bank for Agriculture and Rural Development (NABARD)",
        "post_type": "Banking / Development Finance",
        "notification_date": date(2025, 11, 8),
        "application_deadline": date(2025, 11, 30),
        "exam_date": date(2025, 12, 20),
        "official_pdf_url": "https://www.nabard.org/careers-notices1.aspx?cid=693&id=26",
        "apply_url": "https://nabard.org/career",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 12, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 60.0,
        "state_restriction": None,
        "topics": {
            "Agriculture & Rural Development", "Indian Economy",
            "Quantitative Aptitude", "Logical Reasoning", "English",
            "Computer Knowledge", "Current Affairs", "Banking Awareness"
        }
    },
    {
        "id": "lic-aao",
        "title": "LIC Assistant Administrative Officer (AAO)",
        "organizing_body": "Life Insurance Corporation of India (LIC)",
        "post_type": "Banking / Insurance",
        "notification_date": date(2025, 8, 16),
        "application_deadline": date(2025, 9, 8),
        "exam_date": date(2025, 10, 3),
        "official_pdf_url": "https://licindia.in/recruitment-of-aao-generalists/-specialists/-assistant-engineers-2025",
        "apply_url": "https://licindia.in/careers",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 8, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Reasoning", "Quantitative Aptitude", "English",
            "General Awareness", "Insurance Awareness",
            "Banking Basics", "Current Affairs", "Computer Knowledge"
        }
    },
    {
        "id": "epfo-eo-ao",
        "title": "EPFO Enforcement Officer / Accounts Officer (UPSC CRT, Special Advt 52/2025)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Central Govt / Statutory Body",
        "notification_date": date(2025, 7, 29),
        "application_deadline": date(2025, 8, 18),
        "exam_date": date(2025, 11, 30),
        "official_pdf_url": "https://www.upsc.gov.in/recruitment/recruitment-test/notices",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 30,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Quantitative Aptitude", "Logical Reasoning", "English",
            "General Awareness", "Current Affairs", "Indian Polity",
            "General Science", "Computer Knowledge"
        }
    },

    # ==================== CIVIL SERVICES, DEFENCE & POLICE (EXPANDED) ====================
    {
        "id": "ssc-cpo-sub-inspector",
        "title": "SSC Sub-Inspector (Delhi Police & CAPFs)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Law Enforcement / Police",
        "notification_date": date(2026, 9, 10),
        "application_deadline": date(2026, 9, 30),
        "exam_date": None,
        "official_pdf_url": "https://ssc.gov.in/api/attachment/uploads/masterData/NoticeBoards/Notice_of_adv_capf_2026.pdf",
        "apply_url": "https://ssc.gov.in/home/apply",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 20,
        "max_age_general": 25,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Quantitative Aptitude", "Logical Reasoning", "General Awareness",
            "General Science", "English", "Computer Knowledge",
            "Current Affairs", "Law & Order Basics"
        }
    },
    {
        "id": "upsc-capf-ac",
        "title": "UPSC Central Armed Police Forces (Assistant Commandant)",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "Paramilitary / Officer",
        "notification_date": date(2026, 2, 20),
        "application_deadline": date(2026, 3, 12),
        "exam_date": date(2026, 7, 19),
        "official_pdf_url": "https://www.upsc.gov.in/examinations/Central%20Armed%20Police%20Forces%20%28ACs%29%20Examination%2C%202026",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 20,
        "max_age_general": 25,
        "age_cutoff_date": date(2027, 8, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Indian Polity", "Indian History", "Indian Geography",
            "Indian Economy", "Environment & Ecology", "Internal Security",
            "Current Affairs", "CSAT (Reading Comprehension & Data Interpretation)",
            "Essay Writing", "Reasoning"
        }
    },
    {
        "id": "upsc-cds",
        "title": "UPSC Combined Defence Services (IMA / INA / OTA)",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "Defense / Officer Cadet",
        "notification_date": date(2026, 5, 20),
        "application_deadline": date(2026, 6, 9),
        "exam_date": date(2026, 9, 13),
        "official_pdf_url": "https://www.upsc.gov.in/sites/default/files/Notif-CDS-II-2026-Engl-200526.pdf",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 19,
        "max_age_general": 25,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "General Knowledge", "English", "Elementary Mathematics",
            "Current Affairs", "Logical Reasoning", "General Science"
        }
    },
    {
        "id": "upsc-ies",
        "title": "UPSC Engineering Services (IES / ESE)",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "Engineering / All India Services",
        "notification_date": date(2026, 9, 16),
        "application_deadline": date(2026, 10, 6),
        "exam_date": date(2027, 1, 31),
        "official_pdf_url": "https://www.upsc.gov.in/sites/default/files/Notif-ESEP-2027-Engl-160926.pdf",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["B.Tech", "BE"],
        "allowed_streams": ["Civil", "Mechanical", "Electrical", "Electronics"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Engineering Mathematics", "General Studies & Engineering Ethics",
            "Engineering Aptitude", "Civil Engineering", "Mechanical Engineering",
            "Electrical Engineering", "Electronics & Telecom", "General Awareness"
        }
    },
    {
        "id": "afcat",
        "title": "Indian Air Force AFCAT (Flying & Ground Duty)",
        "organizing_body": "Indian Air Force / CDAC (AFCAT)",
        "post_type": "Defense / Officer",
        "notification_date": None,
        "application_deadline": date(2026, 12, 11),
        "exam_date": date(2027, 1, 31),
        "official_pdf_url": "https://careerairforce.gov.in/sites/default/files/2026-11/Notification-for-AFCAT-2027.pdf",
        "apply_url": "https://afcat.edcil.co.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 20,
        "max_age_general": 26,
        "age_cutoff_date": date(2027, 7, 1),
        "allowed_degrees": ["Any Graduate", "B.Tech", "BE"],
        "allowed_streams": ["Any"],
        "min_percentage": 60.0,
        "state_restriction": None,
        "topics": {
            "General Awareness", "Verbal Ability in English",
            "Numerical Ability", "Reasoning & Military Aptitude",
            "Current Affairs", "Computer Basics"
        }
    },
    {
        "id": "upsc-geologist",
        "title": "UPSC Geologist Examination (GSI)",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "Scientific / Technical (Group-A)",
        "notification_date": date(2026, 9, 2),
        "application_deadline": date(2026, 9, 22),
        "exam_date": date(2027, 1, 10),
        "official_pdf_url": "https://www.upsc.gov.in/sites/default/files/Notif-CGSPE-2027-Engl-020926.pdf",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 24,
        "max_age_general": 32,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["M.Sc", "M.Tech", "M.E"],
        "allowed_streams": ["Geology", "Geophysics", "Earth Sciences"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Mineralogy & Petrology", "Structural Geology", "Remote Sensing & GIS",
            "Indian Geography", "General Science", "Current Affairs",
            "General Studies & Aptitude"
        }
    },

    # ==================== PSU / TECHNICAL ENERGY & IT ====================
    {
        "id": "isro-scientist-b",
        "title": "ISRO Scientist / Engineer (SC)",
        "organizing_body": "Indian Space Research Organisation (ISRO)",
        "post_type": "Technical / Space Research",
        "notification_date": date(2026, 8, 27),
        "application_deadline": date(2026, 9, 16),
        "exam_date": None,
        "official_pdf_url": "https://www.isro.gov.in/ICRB_Recruitment13.html",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 28,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["B.Tech", "BE"],
        "allowed_streams": ["Computer Science", "Information Technology", "Mechanical", "Electronics", "Electrical", "Civil"],
        "min_percentage": 60.0,
        "state_restriction": None,
        "topics": {
            "Engineering Mathematics", "Computer Organization",
            "Data Structures & Algorithms", "Electronics & Communication",
            "Mechanical Engineering (Heat & Power)", "Civil Engineering",
            "General Awareness", "Current Affairs"
        }
    },
    {
        "id": "iocl-officer",
        "title": "IOCL Officer (Engineering / Marketing)",
        "organizing_body": "Indian Oil Corporation Limited (IOCL)",
        "post_type": "PSU Energy / Technical & Management",
        "notification_date": date(2026, 8, 14),
        "application_deadline": date(2026, 9, 3),
        "exam_date": date(2026, 9, 24),
        "official_pdf_url": "https://iocl.com/admin/img/UploadedFiles/LatestJobOpening/Files/DetailedAd14082026.pdf",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["B.Tech", "BE", "MBA"],
        "allowed_streams": ["Mechanical", "Electrical", "Electronics", "Civil", "Chemical"],
        "min_percentage": 60.0,
        "state_restriction": None,
        "topics": {
            "Engineering Mathematics", "Mechanical Engineering",
            "Electrical Engineering", "Chemical Engineering",
            "General Awareness", "Quantitative Aptitude",
            "Reasoning", "Current Affairs"
        }
    },
    {
        "id": "ntpc-executive",
        "title": "NTPC Executive Trainee (ET)",
        "organizing_body": "NTPC Limited",
        "post_type": "PSU Energy / Technical",
        "notification_date": None,
        # No current window exists (pre-GATE-2027 notice only; exact dates not
        # announced). This date is an internal placeholder only — the UI shows
        # "check official notification" (verification_status=check_required) and
        # never displays a guessed date.
        "application_deadline": date(2027, 2, 10),
        "exam_date": None,
        "official_pdf_url": "https://careers.ntpc.co.in/recruitment/",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 22,
        "max_age_general": 30,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["B.Tech", "BE", "MBA"],
        "allowed_streams": ["Mechanical", "Electrical", "Electronics", "Civil"],
        "min_percentage": 60.0,
        "state_restriction": None,
        "topics": {
            "Engineering Mathematics", "Thermodynamics", "Power Plant Engineering",
            "Electrical Machines", "General Awareness",
            "Quantitative Aptitude", "Reasoning", "Current Affairs"
        }
    },
    {
        "id": "bsnl-jto",
        "title": "BSNL Junior Telecom Officer (JTO)",
        "organizing_body": "Bharat Sanchar Nigam Limited (BSNL)",
        "post_type": "PSU / Telecom",
        "notification_date": date(2026, 5, 26),
        "application_deadline": date(2026, 7, 3),
        "exam_date": date(2026, 8, 23),
        "official_pdf_url": "https://externalexam.bsnl.co.in/Examination%20notification%20DR%20JTO(T).pdf",
        "apply_url": "https://externalexam.bsnl.co.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["B.Tech", "BE"],
        "allowed_streams": ["Telecommunication", "Electronics", "Computer Science", "Information Technology", "Electrical"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Engineering Mathematics", "Electronics Devices & Circuits",
            "Signals & Systems", "Digital Communication", "Computer Networks",
            "DBMS & SQL", "General Awareness", "Current Affairs"
        }
    },

    # ==================== TEACHING (CENTRAL) ====================
    # ==================== CURRENTLY OPEN (verified 2026-11-15) ====================
    # Open application windows verified against official notifications on
    # 2026-11-15. Everything else currently live on aggregators that does not
    # fit Prince's profile was deliberately left out to avoid false verdicts.
    {
        "id": "rrb-station-master",
        "title": "RRB Station Master (CEN No. 08/2026)",
        "organizing_body": "Railway Recruitment Boards (RRBs), Ministry of Railways",
        "post_type": "Railways / Station Master",
        "notification_date": date(2026, 10, 26),
        "application_deadline": date(2026, 11, 25),
        "exam_date": None,
        "official_pdf_url": "https://rrb.indianrailways.gov.in/-/image/1793016771817CEN_08_2026_StationMaster.pdf/examsDocuments",
        "apply_url": "https://rrbapply.gov.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 20,
        "max_age_general": 33,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Basic Science & Mathematics", "Data Analysis & Interpretation",
            "Logical Capability", "Mental Reasoning", "Geometry & Trigonometry",
            "Probability & Statistics", "Railway Safety & Operations"
        }
    },
    {
        "id": "dsssb-mts",
        "title": "DSSSB Multi-Tasking Staff (MTS) — Advt No. 06/2026",
        "organizing_body": "Delhi Subordinate Services Selection Board (DSSSB), Govt. of NCT of Delhi",
        "post_type": "Group C / Multi-Tasking Staff",
        "notification_date": date(2026, 11, 6),
        "application_deadline": date(2026, 12, 11),
        "exam_date": None,
        "official_pdf_url": "https://dsssb.delhi.gov.in/sites/default/files/DSSSB/circulars-orders/final_advt_06_2026_j_e_electrical_mts_1.pdf",
        "apply_url": "https://dsssbonline.nic.in",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 27,
        "age_cutoff_date": date(2026, 12, 11),
        "allowed_degrees": ["10th", "10th Pass", "Matriculation", "12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "General Awareness", "General Intelligence & Reasoning",
            "Arithmetical & Numerical Ability",
            "Hindi Language & Comprehension",
            "English Language & Comprehension",
            "Computer Basics"
        }
    },
    {
        "id": "indian-bank-apprentice",
        "title": "Indian Bank Apprentice (Customer Service Associate) — FY 2026-27",
        "organizing_body": "Indian Bank (Public Sector Bank)",
        "post_type": "Contract / Apprentice",
        "notification_date": date(2026, 11, 4),
        "application_deadline": date(2026, 11, 25),
        "exam_date": None,
        "official_pdf_url": "https://indianbank.bank.in/en/career",
        "apply_url": "https://ibpsreg.ibps.in/inbraoct26/",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 20,
        "max_age_general": 28,
        "age_cutoff_date": date(2026, 11, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Reasoning Aptitude", "Computer Knowledge",
            "English Language", "Quantitative Aptitude",
            "General Awareness & Banking Industry", "Current Affairs"
        }
    },
    {
        "id": "nicl-apprentice",
        "title": "NICL Graduate Apprentice 2026-27 (Advt: Engagement of Graduate Apprentices)",
        "organizing_body": "National Insurance Company Limited (NICL)",
        "post_type": "Contract / Apprentice (NATS)",
        "notification_date": date(2026, 11, 4),
        "application_deadline": date(2026, 11, 18),
        "exam_date": None,
        "official_pdf_url": "https://nationalinsurance.nic.co.in/sites/default/files/2026-11/Advertisement%20for%20Engagement%20of%20Apprentices%20for%20the%20year%202026-27.pdf",
        "apply_url": "https://nats.education.gov.in/index.php",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 4, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Data Interpretation", "Logical Reasoning", "English",
            "Quantitative Aptitude", "Current Affairs",
            "General Awareness", "Computer Basics"
        }
    },
    {
        "id": "hcl-apprentice-10th",
        "title": "HCL Trade Apprentice 2026 (10th-pass trades: Mate Mines / Shotfirer / Driver-cum-Mechanic)",
        "organizing_body": "Hindustan Copper Limited (HCL), Malanjkhand Copper Project",
        "post_type": "Contract / Apprentice (Trade Apprentice)",
        "notification_date": date(2026, 11, 3),
        "application_deadline": date(2026, 11, 24),
        "exam_date": None,
        "official_pdf_url": "https://www.hindustancopper.com/Upload/Notice/0-639293279747275000-NoticeFILE.pdf",
        "apply_url": "https://www.hindustancopper.com/ITIApplicationmcp/Login/145",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 25,
        "age_cutoff_date": date(2026, 11, 1),
        "allowed_degrees": ["10th", "10th Pass", "Matriculation"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Basic Mathematics", "General Science", "General Knowledge",
            "Current Affairs", "Physical Fitness"
        }
    },
    {
        "id": "bhu-computer-operator",
        "title": "BHU Computer Operator Grade-I (Advt No. 03/2026-2027, Computer Center)",
        "organizing_body": "Banaras Hindu University (BHU)",
        "post_type": "Group C / Computer Operations",
        "notification_date": date(2026, 10, 26),
        "application_deadline": date(2026, 11, 25),
        "exam_date": None,
        "official_pdf_url": "https://bhu.ac.in/Images/files/Advt_%20No_03_26-27%20for%20Computer%20Center.pdf",
        "apply_url": "https://bhu.ac.in/rac",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 32,
        "age_cutoff_date": date(2026, 11, 25),
        "allowed_degrees": ["BCA", "B.Sc"],
        "allowed_streams": ["Computer Applications", "Computer Science", "Information Technology"],
        "min_percentage": 55.0,
        "state_restriction": None,
        "topics": {
            "Computer Fundamentals", "Programming & Databases",
            "Computer Networks", "Digital Electronics",
            "Quantitative Aptitude", "Reasoning", "Current Affairs"
        }
    },
    {
        "id": "rml-lims-hospital-attendant",
        "title": "Dr RMLIMS Hospital Attendant Grade-II (Advt 81/2026)",
        "organizing_body": "Dr. Ram Manohar Lohia Institute of Medical Sciences (Dr. RMLIMS), Lucknow",
        "post_type": "Group D / Support Staff",
        "notification_date": date(2026, 8, 25),
        "application_deadline": date(2026, 11, 20),
        "exam_date": None,
        "official_pdf_url": "https://www.drrmlims.ac.in/Assets/pages/recruitment/Final_Advt_2026_GROUP_B_C_D_1.pdf",
        "apply_url": "https://www.drrmlims.ac.in/",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 40,
        "age_cutoff_date": date(2026, 11, 20),
        "allowed_degrees": ["10th", "10th Pass", "Matriculation"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "General Knowledge", "Current Affairs", "Reasoning",
            "Elementary Mathematics", "Hindi", "General English",
            "Computer Basics"
        }
    },

    # ==================== ANNOUNCED FUTURE CYCLES (official UPSC Calendar 2027) ====================
    # Dates are taken from the official UPSC Annual Calendar 2027 (released
    # 2026-05-20, upsc.gov.in), NOT from the detailed notification — the detailed
    # notification does not exist yet. Until it does, this row is check_required:
    # the UI shows "Check official notification" and hides these dates; the row
    # expires with the calendar-announced deadline and is re-verified when the
    # actual notification is checked (flip to verified + real application window).
    {
        "id": "upsc-cds-i-2027",
        "title": "UPSC Combined Defence Services Examination (I), 2027",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "Defense / Officer Cadet",
        "notification_date": date(2026, 12, 2),   # announced in UPSC Calendar 2027
        "application_deadline": date(2026, 12, 22),  # announced in UPSC Calendar 2027
        "exam_date": date(2027, 4, 11),              # announced in UPSC Calendar 2027
        "official_pdf_url": "https://www.upsc.gov.in/sites/default/files/Calendar-Year-2027-Engl-200526.pdf",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 19,
        "max_age_general": 25,
        "age_cutoff_date": date(2027, 4, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "General Knowledge", "English", "Elementary Mathematics",
            "Current Affairs", "Logical Reasoning", "General Science"
        }
    },
    {
        "id": "upsc-nda-i-2027",
        "title": "UPSC National Defence Academy & Naval Academy Examination (I), 2027",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "Defense / Officer Cadet",
        "notification_date": date(2026, 12, 2),   # announced in UPSC Calendar 2027
        "application_deadline": date(2026, 12, 22),  # announced in UPSC Calendar 2027
        "exam_date": date(2027, 4, 11),              # announced in UPSC Calendar 2027
        "official_pdf_url": "https://www.upsc.gov.in/sites/default/files/Calendar-Year-2027-Engl-200526.pdf",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 16,
        "max_age_general": 19,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["PCM (Physics, Chemistry, Maths)", "PCM", "Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Algebra", "Trigonometry", "Matrices & Determinants", "Calculus",
            "Vector Algebra", "Statistics & Probability", "Physics", "Chemistry",
            "General Science", "History & Freedom Movement", "Geography", "Current Affairs", "English Grammar"
        }
    },
    {
        "id": "upsc-cse-2027",
        "title": "UPSC Civil Services Examination (Preliminary), 2027",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "All India Services",
        "notification_date": date(2027, 1, 13),   # announced in UPSC Calendar 2027
        "application_deadline": date(2027, 2, 2),  # announced in UPSC Calendar 2027
        "exam_date": date(2027, 5, 23),             # announced in UPSC Calendar 2027
        "official_pdf_url": "https://www.upsc.gov.in/sites/default/files/Calendar-Year-2027-Engl-200526.pdf",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 21,
        "max_age_general": 32,
        "age_cutoff_date": date(2027, 8, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Indian Polity", "Modern History", "Ancient & Medieval History",
            "Physical & Indian Geography", "Indian Economy", "Environment & Ecology",
            "Science & Technology", "Current Affairs", "Ethics, Integrity & Aptitude",
            "Reading Comprehension", "Data Interpretation", "Essay Writing"
        }
    },
    {
        "id": "upsc-capf-ac-2027",
        "title": "UPSC Central Armed Police Forces (Assistant Commandant) Examination, 2027",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "Paramilitary / Officer",
        "notification_date": date(2027, 2, 17),   # announced in UPSC Calendar 2027
        "application_deadline": date(2027, 3, 9),  # announced in UPSC Calendar 2027
        "exam_date": date(2027, 7, 4),             # announced in UPSC Calendar 2027
        "official_pdf_url": "https://www.upsc.gov.in/sites/default/files/Calendar-Year-2027-Engl-200526.pdf",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 20,
        "max_age_general": 25,
        "age_cutoff_date": date(2027, 7, 4),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Indian Polity", "Indian History", "Indian Geography",
            "Indian Economy", "Environment & Ecology", "Internal Security",
            "Current Affairs", "CSAT (Reading Comprehension & Data Interpretation)",
            "Essay Writing", "Reasoning"
        }
    },
    {
        "id": "kvs-tgt",
        "title": "KVS Trained Graduate Teacher (TGT) / PGT",
        "organizing_body": "Kendriya Vidyalaya Sangathan (KVS)",
        "post_type": "Teaching / Central Schools",
        "notification_date": date(2025, 11, 13),
        "application_deadline": date(2025, 12, 11),
        "exam_date": None,
        "official_pdf_url": "https://cdnbbsr.s3waas.gov.in/s32d2ca7eedf739ef4c3800713ec482e1a/uploads/2025/11/2025111348.pdf",
        "verified_on": date(2026, 11, 15),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 40,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Any Graduate", "B.Sc", "BA", "B.Com"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {
            "Subject Pedagogy", "Child Development & Pedagogy",
            "Constitution & Governance", "Current Affairs",
            "General Awareness", "Reasoning", "English", "Hindi"
        }
    },
    {
        "id": "bpsc-auditor-mains-2026",
        "title": "BPSC Auditor Main Written Exam 2026 (Mains-qualified candidates only)",
        "organizing_body": "Bihar Public Service Commission (BPSC)",
        "post_type": "State / Bihar / Accounts",
        "notification_date": date(2026, 10, 26),
        "application_deadline": date(2026, 11, 16),
        "exam_date": None,
        "official_pdf_url": "https://bpsc.bihar.gov.in/wp-content/uploads/BPSC_content/Notices/Advertisement-092026-Auditor-Main-Written-Examination_BPSC-20261026-tfda2u.pdf",
        "apply_url": "https://bpsc.bihar.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 37,
        "age_cutoff_date": date(2025, 8, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Commerce"],
        "min_percentage": 0.0,
        "state_restriction": "Bihar",
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "upsssc-inter-level-2026",
        "title": "UPSSSC Intermediate Level Main Exam 2026 — 1,784 posts (Advt 26-Exam/2026)",
        "organizing_body": "Uttar Pradesh Subordinate Services Selection Commission (UPSSSC)",
        "post_type": "State / UP / Intermediate",
        "notification_date": date(2026, 10, 16),
        "application_deadline": date(2026, 12, 1),
        "exam_date": None,
        "official_pdf_url": "https://upsssc.gov.in",
        "apply_url": "https://upsssc.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 40,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": "Uttar Pradesh",
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "assam-rifles-tradesman-2026",
        "title": "Assam Rifles Technical & Tradesman Recruitment Rally 2026 — 354 posts",
        "organizing_body": "Directorate General Assam Rifles (Ministry of Home Affairs)",
        "post_type": "Defence / Tradesman",
        "notification_date": date(2026, 11, 3),
        "application_deadline": date(2026, 12, 14),
        "exam_date": None,
        "official_pdf_url": "https://assamrifles.gov.in",
        "apply_url": "https://assamrifles.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 17,
        "max_age_general": 25,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "rrc-nr-apprentice-2026",
        "title": "RRC NR Act Apprentice 2026 — 4,651 seats",
        "organizing_body": "Railway Recruitment Cell, Northern Railway (RRC NR)",
        "post_type": "Railways / Apprentice",
        "notification_date": date(2026, 11, 6),
        "application_deadline": date(2026, 12, 11),
        "exam_date": None,
        "official_pdf_url": "https://www.rrcnr.org/downloads/Notification_Act_Appretice_2026.pdf",
        "apply_url": "https://www.rrcnr.org",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 15,
        "max_age_general": 24,
        "age_cutoff_date": date(2026, 11, 11),
        "allowed_degrees": ["ITI"],
        "allowed_streams": ["Any"],
        "min_percentage": 50.0,
        "state_restriction": None,
        "topics": {"Engineering Mechanics","Thermodynamics","Fluid Mechanics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "upessc-tgt-2026",
        "title": "UPESSC Assistant Teacher (TGT) 2026 — 17,735 posts (Advt 07/2026)",
        "organizing_body": "Uttar Pradesh Education Service Selection Commission (UPESSC)",
        "post_type": "Teaching / UP / TGT",
        "notification_date": date(2026, 10, 23),
        "application_deadline": date(2026, 11, 23),
        "exam_date": None,
        "official_pdf_url": "https://upessc.up.gov.in/Notice/bc7b-da7d-4adb-b354-d265.pdf",
        "apply_url": "https://apply.upessc.org",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 62,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 45.0,
        "state_restriction": "Uttar Pradesh",
        "topics": {"Subject Pedagogy","Child Development & Pedagogy","Indian Polity","Constitution & Governance","Current Affairs","General Awareness","Reasoning","English","Hindi"}
    },
    {
        "id": "upessc-principal-2026",
        "title": "UPESSC Principal (Aided Schools) 2026 — 1,475 posts (Advt 08/2026)",
        "organizing_body": "Uttar Pradesh Education Service Selection Commission (UPESSC)",
        "post_type": "Teaching / UP / Principal",
        "notification_date": date(2026, 10, 23),
        "application_deadline": date(2026, 11, 22),
        "exam_date": None,
        "official_pdf_url": "https://upessc.up.gov.in/Notice/5520-7034-4820-d1bb-554c.pdf",
        "apply_url": "https://apply.upessc.org",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 30,
        "max_age_general": 62,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 50.0,
        "state_restriction": "Uttar Pradesh",
        "topics": {"Subject Pedagogy","Child Development & Pedagogy","Indian Polity","Constitution & Governance","Current Affairs","General Awareness","Reasoning","English","Hindi"}
    },
    {
        "id": "upessc-headmaster-2026",
        "title": "UPESSC Headmaster (Aided Schools) 2026 — 1,172 posts (Advt 09/2026)",
        "organizing_body": "Uttar Pradesh Education Service Selection Commission (UPESSC)",
        "post_type": "Teaching / UP / Headmaster",
        "notification_date": date(2026, 10, 23),
        "application_deadline": date(2026, 11, 22),
        "exam_date": None,
        "official_pdf_url": "https://upessc.up.gov.in/Notice/5520-7034-4820-d1bb-554c.pdf",
        "apply_url": "https://apply.upessc.org",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 30,
        "max_age_general": 62,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 50.0,
        "state_restriction": "Uttar Pradesh",
        "topics": {"Subject Pedagogy","Child Development & Pedagogy","Indian Polity","Constitution & Governance","Current Affairs","General Awareness","Reasoning","English","Hindi"}
    },
    {
        "id": "isro-ursc-2026",
        "title": "ISRO URSC Various Post 2026 (Technician B / Heavy & Light Vehicle Driver A)",
        "organizing_body": "U R Rao Satellite Centre (URSC) / ISRO",
        "post_type": "Space / Technical / 10th",
        "notification_date": date(2026, 10, 24),
        "application_deadline": date(2026, 11, 20),
        "exam_date": None,
        "official_pdf_url": "https://www.isro.gov.in/media_isro/pdf/recruitmentNotice/2026/Oct/URSClAdvt2410_24102026.pdf",
        "apply_url": "https://www.isro.gov.in/URSCRecruitment13.html",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 35,
        "age_cutoff_date": date(2026, 11, 13),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "exim-bank-mt-manager-2026",
        "title": "India Exim Bank MT & Manager 2026 — 120 posts (Advt HRM/MT/M/2026-27/05)",
        "organizing_body": "Export-Import Bank of India (India Exim Bank)",
        "post_type": "Banking / PSU / Officers",
        "notification_date": date(2026, 11, 12),
        "application_deadline": date(2026, 12, 11),
        "exam_date": None,
        "official_pdf_url": "https://eximbankindia.in/careers",
        "apply_url": "https://eximbankindia.in/careers",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 28,
        "age_cutoff_date": date(2026, 11, 1),
        "allowed_degrees": ["MBA"],
        "allowed_streams": ["Any"],
        "min_percentage": 60.0,
        "state_restriction": None,
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "upsssc-je-mechanical-2026",
        "title": "UPSSSC Junior Engineer (Mechanical) 2026 — 1,156 posts (Advt 24-Exam/2026)",
        "organizing_body": "Uttar Pradesh Subordinate Services Selection Commission (UPSSSC)",
        "post_type": "State / Engineers / Diploma",
        "notification_date": date(2026, 10, 12),
        "application_deadline": date(2026, 11, 25),
        "exam_date": None,
        "official_pdf_url": "https://upsssc.gov.in",
        "apply_url": "https://upsssc.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 40,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Mechanical"],
        "min_percentage": 0.0,
        "state_restriction": "Uttar Pradesh",
        "topics": {"Engineering Mechanics","Thermodynamics","Fluid Mechanics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "rrc-nwr-apprentice-2026",
        "title": "RRC NWR Act Apprentice 2026 — 2,008 seats",
        "organizing_body": "Railway Recruitment Cell, North Western Railway (RRC NWR)",
        "post_type": "Railways / Apprentice",
        "notification_date": date(2026, 10, 21),
        "application_deadline": date(2026, 11, 22),
        "exam_date": None,
        "official_pdf_url": "https://rrcjaipur.in/storeWebFiles/1008_11718187.PDF",
        "apply_url": "https://rrcactapp.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 15,
        "max_age_general": 24,
        "age_cutoff_date": date(2026, 11, 22),
        "allowed_degrees": ["ITI"],
        "allowed_streams": ["Any"],
        "min_percentage": 50.0,
        "state_restriction": None,
        "topics": {"Engineering Mechanics","Thermodynamics","Fluid Mechanics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "afms-medical-officer-2026",
        "title": "AFMS Medical Officer (SSC) 2026 — 120 posts",
        "organizing_body": "Armed Forces Medical Services (DGAFMS)",
        "post_type": "Defence / Medical",
        "notification_date": date(2026, 11, 7),
        "application_deadline": date(2026, 11, 18),
        "exam_date": None,
        "official_pdf_url": "https://join.afms.gov.in",
        "apply_url": "https://join.afms.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 12, 31),
        "allowed_degrees": ["MBBS"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "rrc-cr-apprentice-2026",
        "title": "RRC CR Act Apprentice 2026 — 3,809 seats (incl. Addendum 10.11.2026)",
        "organizing_body": "Railway Recruitment Cell, Central Railway (RRC CR)",
        "post_type": "Railways / Apprentice",
        "notification_date": date(2026, 11, 3),
        "application_deadline": date(2026, 12, 2),
        "exam_date": None,
        "official_pdf_url": "https://www.rrccr.com/rrwc/Files/7131ab94-6fc8-45c1-a2ed-f9191914dcbd.pdf",
        "apply_url": "https://www.rrccr.com/TradeApp/login/Index",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 15,
        "max_age_general": 24,
        "age_cutoff_date": date(2026, 11, 3),
        "allowed_degrees": ["ITI"],
        "allowed_streams": ["Any"],
        "min_percentage": 50.0,
        "state_restriction": None,
        "topics": {"Engineering Mechanics","Thermodynamics","Fluid Mechanics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "bihar-vidhan-sabha-attendant-2026",
        "title": "Bihar Vidhan Sabha Office Attendant 2026 — 5 posts (Advt 02/2026)",
        "organizing_body": "Bihar Legislative Assembly (Vidhan Sabha) Secretariat",
        "post_type": "State / Bihar / 10th",
        "notification_date": date(2026, 11, 4),
        "application_deadline": date(2026, 12, 6),
        "exam_date": None,
        "official_pdf_url": "https://vidhansabha.bihar.gov.in",
        "apply_url": "https://blasrecruit.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 37,
        "age_cutoff_date": date(2026, 8, 1),
        "allowed_degrees": ["10th"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": "Bihar",
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "bihar-vidhan-sabha-jsa-2026",
        "title": "Bihar Vidhan Sabha Junior Secretariat Assistant 2026 — 15 posts (Advt 01/2026)",
        "organizing_body": "Bihar Legislative Assembly (Vidhan Sabha) Secretariat",
        "post_type": "State / Bihar / 12th",
        "notification_date": date(2026, 11, 4),
        "application_deadline": date(2026, 12, 6),
        "exam_date": None,
        "official_pdf_url": "https://vidhansabha.bihar.gov.in",
        "apply_url": "https://blasrecruit.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 37,
        "age_cutoff_date": date(2026, 8, 1),
        "allowed_degrees": ["12th"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": "Bihar",
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "up-anganwadi-bharti-2026",
        "title": "UP Anganwadi Worker & Helper Recruitment 2026 (District-wise)",
        "organizing_body": "UP Govt — ICDS (Bal Vikas Seva & Pushtahar) + District Programme Officers",
        "post_type": "State / UP / Social Welfare / Women",
        "notification_date": date(2026, 11, 12),
        "application_deadline": date(2026, 12, 3),
        "exam_date": None,
        "official_pdf_url": "https://upanganwadibharti.in",
        "apply_url": "https://upanganwadibharti.in",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 18,
        "max_age_general": 35,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["10th"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": "Uttar Pradesh",
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "rrb-isolated-categories-2026",
        "title": "RRB CEN 09/2026 — Isolated Categories — 191 posts",
        "organizing_body": "Railway Recruitment Boards",
        "post_type": "Railways / Isolated",
        "notification_date": date(2026, 10, 24),
        "application_deadline": date(2026, 12, 4),
        "exam_date": None,
        "official_pdf_url": "https://www.rrb.indianrailways.gov.in",
        "apply_url": "https://rrbapply.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 40,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["Specialist / Post-Wise"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Percentages","Ratio & Proportion","Algebra","Geometry","Trigonometry","Elementary Science","History & Freedom Movement","Geography","Current Affairs","General Hindi","English Grammar","General Science"}
    },
    {
        "id": "upsssc-je-electrical-2026",
        "title": "UPSSSC Junior Engineer (Electrical) 2026 — 380 posts (Advt 25-Exam/2026)",
        "organizing_body": "Uttar Pradesh Subordinate Services Selection Commission (UPSSSC)",
        "post_type": "State / Engineers / Diploma",
        "notification_date": date(2026, 10, 12),
        "application_deadline": date(2026, 11, 27),
        "exam_date": None,
        "official_pdf_url": "https://upsssc.gov.in",
        "apply_url": "https://upsssc.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 40,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Electrical"],
        "min_percentage": 0.0,
        "state_restriction": "Uttar Pradesh",
        "topics": {"Engineering Mechanics","Thermodynamics","Fluid Mechanics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "isro-sdsc-shar-apprentice-2026",
        "title": "ISRO SDSC SHAR Apprentice 2026 (Graduate & Technician) — 400 seats",
        "organizing_body": "Satish Dhawan Space Centre SHAR / ISRO",
        "post_type": "Space / Apprentice",
        "notification_date": date(2026, 11, 6),
        "application_deadline": date(2026, 11, 26),
        "exam_date": None,
        "official_pdf_url": "https://apps.shar.gov.in/sdscshar/apprentice/Apprenticeship2026.pdf",
        "apply_url": "https://nats.education.gov.in",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 15,
        "max_age_general": 35,
        "age_cutoff_date": date(2026, 11, 6),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Engineering Mechanics","Thermodynamics","Fluid Mechanics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "upsc-13-2026",
        "title": "UPSC Advertisement No. 13/2026 — Various Posts (14 Nov – 4 Dec 2026)",
        "organizing_body": "Union Public Service Commission (UPSC)",
        "post_type": "Central Govt / Various",
        "notification_date": date(2026, 11, 13),
        "application_deadline": date(2026, 12, 4),
        "exam_date": None,
        "official_pdf_url": "https://www.upsc.gov.in/sites/default/files/AdvtNo-13-2026-Engl-131126_0.pdf",
        "apply_url": "https://upsconline.nic.in",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 21,
        "max_age_general": 45,
        "age_cutoff_date": date(2026, 12, 4),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Percentages","Ratio & Proportion","Algebra","Current Affairs","General Science","Physical Science","History","Geography","Reasoning"}
    },
    {
        "id": "asrb-icar-ta-2026",
        "title": "ASRB ICAR Technical Assistant 2026 — 1,393 posts",
        "organizing_body": "Agricultural Scientists Recruitment Board (ASRB) — ICAR",
        "post_type": "Agriculture / Technical",
        "notification_date": date(2026, 11, 11),
        "application_deadline": date(2026, 12, 17),
        "exam_date": None,
        "official_pdf_url": "https://asrb.gov.in",
        "apply_url": "https://asrb.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 30,
        "age_cutoff_date": date(2026, 12, 17),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Percentages","Ratio & Proportion","Algebra","Current Affairs","General Science","Physical Science","History","Geography","Reasoning"}
    },
    {
        "id": "uppsc-various-posts-2026",
        "title": "UPPSC Recruitment 2026 — 25 posts (Advt A-5/E-1/2026)",
        "organizing_body": "Uttar Pradesh Public Service Commission (UPPSC), Prayagraj",
        "post_type": "State / UP / Various",
        "notification_date": date(2026, 11, 4),
        "application_deadline": date(2026, 12, 4),
        "exam_date": None,
        "official_pdf_url": "https://uppsc.up.nic.in",
        "apply_url": "https://uppsc.up.nic.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 40,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": "Uttar Pradesh",
        "topics": {"Percentages","Ratio & Proportion","Algebra","Current Affairs","General Science","Physical Science","History","Geography","Reasoning"}
    },
    {
        "id": "bihar-bceceb-sr-resident-2026",
        "title": "BCECEB Senior Resident / Tutor 2026 — 575 posts (PG/MD posts)",
        "organizing_body": "Bihar Combined Entrance Competitive Examination Board (BCECEB)",
        "post_type": "Medical / Bihar / PG",
        "notification_date": date(2026, 11, 2),
        "application_deadline": date(2026, 11, 23),
        "exam_date": None,
        "official_pdf_url": "https://bceceboard.bihar.gov.in",
        "apply_url": "https://bceceboard.bihar.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 37,
        "age_cutoff_date": date(2026, 11, 23),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": "Bihar",
        "topics": {"Percentages","Ratio & Proportion","Algebra","Current Affairs","General Science","Physical Science","History","Geography","Reasoning"}
    },
    {
        "id": "pgcil-et-2026",
        "title": "POWERGRID Engineer Trainee 2026 — 319 posts (through GATE 2026)",
        "organizing_body": "POWERGRID Corporation of India Ltd. (PGCIL)",
        "post_type": "PSU / Engineering / GATE",
        "notification_date": date(2026, 11, 3),
        "application_deadline": date(2026, 11, 18),
        "exam_date": None,
        "official_pdf_url": "https://www.powergrid.in/en/job-opportunities/recruitment-engineer-trainees-2026-through-gate-2026-advt-no-cc042025-dated",
        "apply_url": "https://www.powergrid.in/en/job-opportunities",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 28,
        "age_cutoff_date": date(2026, 12, 31),
        "allowed_degrees": ["B.Tech"],
        "allowed_streams": ["Electrical", "Civil", "Computer Science"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Engineering Mechanics","Thermodynamics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "scl-recruitment-2026",
        "title": "SCL Semi-Conductor Laboratory Recruitment 2026 — 83 posts (Advt SCL:DR:01/2026)",
        "organizing_body": "Semi-Conductor Laboratory (SCL), MeitY, Mohali",
        "post_type": "Govt / Technical / Mohali",
        "notification_date": date(2026, 10, 22),
        "application_deadline": date(2026, 11, 30),
        "exam_date": None,
        "official_pdf_url": "https://www.scl.gov.in/career.html",
        "apply_url": "https://www.scl.gov.in/career.html",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 35,
        "age_cutoff_date": date(2026, 11, 30),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Engineering Mechanics","Thermodynamics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "ongc-apprentice-2026",
        "title": "ONGC Apprentice 2026 — 3,047 seats (Advt ONGC/APPR/1/2026)",
        "organizing_body": "Oil and Natural Gas Corporation Ltd. (ONGC)",
        "post_type": "Apprenticeship",
        "notification_date": date(2026, 10, 29),
        "application_deadline": date(2026, 11, 20),
        "exam_date": None,
        "official_pdf_url": "https://www.ongcindia.com/documents/77751/2660534/Advertisement-engagement-Apprentices2026-27.pdf/e926a825-c08b-6403-60f1-ea0232bcaab8",
        "apply_url": "https://apprenticeshipindia.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 24,
        "age_cutoff_date": date(2026, 10, 29),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Engineering Mechanics","Thermodynamics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "aees-teaching-2026",
        "title": "AEES Teaching Recruitment 2026 — 254 posts (Advt 01/2026)",
        "organizing_body": "Atomic Energy Education Society (AEES), Dept. of Atomic Energy",
        "post_type": "Teaching / All India",
        "notification_date": date(2026, 11, 2),
        "application_deadline": date(2026, 11, 22),
        "exam_date": None,
        "official_pdf_url": "https://www.aees.gov.in",
        "apply_url": "https://www.aees.gov.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 21,
        "max_age_general": 55,
        "age_cutoff_date": date(2026, 11, 22),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Subject Pedagogy","Child Development & Pedagogy","Indian Polity","Current Affairs","General Awareness","Reasoning","English"}
    },
    {
        "id": "nta-jee-main-2027",
        "title": "NTA JEE (Main) 2027 Session-I Registration — Engineering entrance",
        "organizing_body": "National Testing Agency (NTA)",
        "post_type": "Entrance Examination",
        "notification_date": date(2026, 10, 24),
        "application_deadline": date(2026, 11, 22),
        "exam_date": None,
        "official_pdf_url": "https://jeemain.nta.nic.in",
        "apply_url": "https://jeemain.nta.nic.in/online-application-form-for-jee-main-2027-session-1",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 16,
        "max_age_general": 99,
        "age_cutoff_date": date(2026, 11, 22),
        "allowed_degrees": ["12th"],
        "allowed_streams": ["PCM"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Engineering Mechanics","Thermodynamics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "bhel-artisan-2026",
        "title": "BHEL Artisan Various Trade Recruitment 2026 — 660 posts (Advt 01/2026)",
        "organizing_body": "Bharat Heavy Electricals Ltd. (BHEL)",
        "post_type": "PSU / Technical / ITI",
        "notification_date": date(2026, 10, 19),
        "application_deadline": date(2026, 11, 18),
        "exam_date": None,
        "official_pdf_url": "https://careers.bhel.in",
        "apply_url": "https://careers.bhel.in",
        "verified_on": date(2026, 11, 16),
        "verification_status": "verified",
        "min_age": 18,
        "max_age_general": 27,
        "age_cutoff_date": date(2026, 10, 1),
        "allowed_degrees": ["ITI"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Engineering Mechanics","Thermodynamics","Electrical Machines","Building Materials","Constitution of India","Current Affairs","General Science","Mathematics","Physics & Chemistry"}
    },
    {
        "id": "sci-junior-court-attendant-2026",
        "title": "Supreme Court Junior Court Attendant 2026 — 130 tentative posts (Advt F.3/2026-SC(RC))",
        "organizing_body": "Supreme Court of India",
        "post_type": "Judiciary / Group C",
        "notification_date": date(2026, 10, 15),
        "application_deadline": date(2026, 11, 25),
        "exam_date": None,
        "official_pdf_url": "https://www.sci.gov.in/recruitments",
        "apply_url": "https://www.sci.gov.in",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 18,
        "max_age_general": 45,
        "age_cutoff_date": date(2026, 10, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Percentages","Ratio & Proportion","Algebra","Current Affairs","General Science","Physical Science","History","Geography","Reasoning"}
    },
    {
        "id": "sci-court-assistant-2026",
        "title": "Supreme Court Court Assistant (Technical Asst-cum-Programmer) 2026 — 15 posts",
        "organizing_body": "Supreme Court of India",
        "post_type": "Judiciary / Technical",
        "notification_date": date(2026, 10, 2),
        "application_deadline": date(2026, 11, 24),
        "exam_date": None,
        "official_pdf_url": "https://www.sci.gov.in/recruitments",
        "apply_url": "https://www.sci.gov.in",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 18,
        "max_age_general": 40,
        "age_cutoff_date": date(2026, 10, 1),
        "allowed_degrees": ["Specialist / See Notification"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": None,
        "topics": {"Percentages","Ratio & Proportion","Algebra","Current Affairs","General Science","Physical Science","History","Geography","Reasoning"}
    },

    # ---- Aggregator-discovered 2026 jobs (sarkariresult.com.cm). Data extracted from the
    # listed notice pages; verification_status=check_required until confirmed against the
    # board's own notification. source_url keeps the discovery provenance. ----
    {
        "id": "uptet-feb-2027",
        "source_url": "https://sarkariresult.com.cm/uptet-2027-feb-exam/",  # aggregator discovery page; not an official board link
        "title": "UPTET February 2027 (Uttar Pradesh Teacher Eligibility Test)",
        "organizing_body": "Uttar Pradesh Education Service Selection Commission (UPESSC)",
        "post_type": "State / UP / Teacher Eligibility Test",
        "notification_date": date(2026, 11, 19),
        "application_deadline": date(2026, 12, 23),
        "exam_date": date(2027, 2, 26),
        "official_pdf_url": None,  # short notice only; detailed notification not yet published
        "apply_url": "https://upessc.up.gov.in/",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 18,
        "max_age_general": 40,  # age limit N/A in notice; generic placeholder pending verification
        "age_cutoff_date": date(2026, 12, 23),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 50.0,
        "state_restriction": "Uttar Pradesh",
        "allows_final_year": True,
        "topics": {"Child Development & Pedagogy", "General Intelligence", "Reasoning", "Language I", "Language II", "Mathematics", "Science", "Social Studies", "Teaching Aptitude"},
    },
    {
        "id": "haryana-htet-2026",
        "source_url": "https://sarkariresult.com.cm/haryana-htet-online-form-2026/",  # aggregator discovery page; not an official board link
        "title": "Haryana HTET 2026 (Teacher Eligibility Test — PRT / TGT / PGT)",
        "organizing_body": "Board of School Education Haryana (BSEH)",
        "post_type": "State / Haryana / Teacher Eligibility Test",
        "notification_date": date(2026, 11, 19),
        "application_deadline": date(2026, 11, 27),
        "exam_date": date(2026, 12, 26),
        "official_pdf_url": "https://htet2026.org/htet2023/Information_Bulletin%20HTET-2026.pdf",
        "apply_url": "https://htet2026.org/",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 18,
        "max_age_general": 40,  # age limit N/A in notice; generic placeholder pending verification
        "age_cutoff_date": date(2026, 11, 27),
        "allowed_degrees": ["12th", "Any Graduate", "B.Ed"],
        "allowed_streams": ["Any"],
        "min_percentage": 50.0,
        "state_restriction": "Haryana",
        "topics": {"Child Development & Pedagogy", "General Intelligence", "Reasoning", "English", "Hindi", "Mathematics", "Science", "Social Studies", "Teaching Aptitude"},
    },
    {
        "id": "uksssc-constable-various-2026",
        "source_url": "https://sarkariresult.com.cm/uksssc-police-constable-2026/",  # aggregator discovery page; not an official board link
        "title": "UKSSSC Constable Various Posts 2026 (Constable / PAC-IRB / Fireman / Forest Guard / Jail Warder) — 1,694 posts",
        "organizing_body": "Uttarakhand Subordinate Service Selection Commission (UKSSSC)",
        "post_type": "State / Uttarakhand / Police & Constabulary",
        "notification_date": date(2026, 11, 19),
        "application_deadline": date(2026, 12, 25),
        "exam_date": None,
        "official_pdf_url": "https://cdnbbsr.s3waas.gov.in/s34ffd0e19d2069412274bd3025b0e176c/uploads/2026/11/20261117947374675.pdf",
        "apply_url": "https://sssc.uk.gov.in/",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 18,
        "max_age_general": 25,  # post-wise 25-35; general minimum used here
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["12th", "12th Pass", "Intermediate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": "Uttarakhand",
        "topics": {"General Intelligence", "Reasoning", "General Knowledge", "Current Affairs", "English", "Hindi", "Numerical Ability"},
    },
    {
        "id": "rssb-je-reopen-2026",
        "source_url": "https://sarkariresult.com.cm/rssb-junior-engineer-2026/",  # aggregator discovery page; not an official board link
        "title": "RSSB Junior Engineer (JE) 2026 — Re-Open (Advt 10/2026) — 1,909 posts",
        "organizing_body": "Rajasthan Staff Selection Board (RSSB)",
        "post_type": "State / Rajasthan / Engineering",
        "notification_date": date(2026, 11, 17),
        "application_deadline": date(2026, 12, 17),
        "exam_date": None,
        "official_pdf_url": "https://rssb.rajasthan.gov.in/storage/advertisement_item/1786782151.pdf",
        "apply_url": "https://rssb.rajasthan.gov.in/",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 18,
        "max_age_general": 40,
        "age_cutoff_date": date(2027, 1, 1),
        "allowed_degrees": ["B.Tech", "BE", "Diploma"],
        "allowed_streams": ["Electronics", "Mechanical", "Civil", "Electrical"],
        "min_percentage": 0.0,
        "state_restriction": "Rajasthan",
        "topics": {"General Intelligence", "Reasoning", "General Knowledge", "Current Affairs", "Mathematics", "Electrical Engineering", "Mechanical Engineering", "Civil Engineering", "Hindi"},
    },
    {
        "id": "uppsc-ro-aro-2026",
        "source_url": "https://sarkariresult.com.cm/uppsc-ro-aro-oct26/",  # aggregator discovery page; not an official board link
        "title": "UPPSC Review Officer / Assistant Review Officer (RO / ARO) 2026 — 501 posts (Advt A-4/E-1/2026)",
        "organizing_body": "Uttar Pradesh Public Service Commission (UPPSC)",
        "post_type": "State / UP / Review Officer",
        "notification_date": date(2026, 11, 14),
        "application_deadline": date(2026, 11, 26),
        "exam_date": None,
        "official_pdf_url": None,  # notice hosted on UPPSC notifications page; PDF link not on aggregator page
        "apply_url": "https://uppsc.up.nic.in/CandidatePages/Notifications.aspx",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 21,
        "max_age_general": 40,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": "Uttar Pradesh",
        "topics": {"General Intelligence", "Reasoning", "General Knowledge", "Current Affairs", "English", "Hindi", "Quantitative Aptitude", "Computer Knowledge"},
    },
    {
        "id": "ukpsc-lower-pcs-2026",
        "source_url": "https://sarkariresult.com.cm/ukpsc-lower-pcs-2026/",  # aggregator discovery page; not an official board link
        "title": "UKPSC Lower Subordinate Services (Lower PCS) 2026 — 54 posts (Advt A-1/E-2/DR/LSS/2026-27)",
        "organizing_body": "Uttarakhand Public Service Commission (UKPSC)",
        "post_type": "State / Uttarakhand / Lower PCS",
        "notification_date": date(2026, 11, 12),
        "application_deadline": date(2026, 11, 26),
        "exam_date": None,
        "official_pdf_url": None,  # PDF copies hosted on aggregator CDN; official set on UKPSC site
        "apply_url": "https://pscuk.net.in/",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 21,
        "max_age_general": 42,
        "age_cutoff_date": date(2026, 7, 1),
        "allowed_degrees": ["Any Graduate"],
        "allowed_streams": ["Any"],
        "min_percentage": 0.0,
        "state_restriction": "Uttarakhand",
        "topics": {"General Intelligence", "Reasoning", "General Knowledge", "Current Affairs", "English", "Hindi", "Quantitative Aptitude"},
    },
    {
        "id": "rssb-support-engineer-2025",
        "source_url": "https://sarkariresult.com.cm/rssb-support-engineer-recruitment-2025/",  # aggregator discovery page; not an official board link
        "title": "RSSB Support Engineer / Support Chemist 2025 — 1,050 posts (short notice)",
        "organizing_body": "Rajasthan Staff Selection Board (RSSB)",
        "post_type": "State / Rajasthan / Engineering",
        "notification_date": date(2025, 7, 17),
        "application_deadline": date(2026, 12, 31),  # aggregator says "Available Soon"; placeholder to keep row active
        "exam_date": None,
        "official_pdf_url": "https://rssb.rajasthan.gov.in/storage/advertisement_item/1752745060.pdf",
        "apply_url": "https://rssb.rajasthan.gov.in/",
        "verified_on": None,
        "verification_status": "check_required",
        "min_age": 21,
        "max_age_general": 40,
        "age_cutoff_date": date(2026, 1, 1),
        "allowed_degrees": ["B.Tech", "BE", "Diploma", "M.Sc"],
        "allowed_streams": ["Civil", "Mechanical", "Electrical", "Computer Science", "Information Technology"],
        "min_percentage": 0.0,
        "state_restriction": "Rajasthan",
        "topics": {"General Intelligence", "Reasoning", "General Knowledge", "Current Affairs", "Mathematics", "Civil Engineering", "Mechanical Engineering", "Electrical Engineering", "Computer Science"},
    },
]

# Admin-approved job discoveries are persisted in a small JSON overlay and
# become part of the same SEED_EXAMS list used by upsert_seed_exams(). Exactly
# the admit-card overlay pattern — no second publishing pipeline.
APPROVED_JOB_SEED_PATH = Path(
    os.environ.get("JOB_DISCOVERY_SEED_OVERLAY")
    or Path(__file__).with_name("approved_job_discoveries.json")
)

_JOB_DATE_FIELDS = (
    "notification_date", "application_start_date", "application_deadline", "exam_date",
    "age_cutoff_date", "verified_on", "last_checked_at",
)


def load_approved_job_discoveries() -> list[dict]:
    try:
        data = json.loads(APPROVED_JOB_SEED_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        for exam in data:
            for field in _JOB_DATE_FIELDS:
                if isinstance(exam.get(field), str):
                    exam[field] = date.fromisoformat(exam[field])
            if isinstance(exam.get("topics"), list):
                exam["topics"] = set(exam["topics"])
        return data
    except (FileNotFoundError, json.JSONDecodeError, OSError, ValueError):
        return []


def record_approved_job_seed(item: dict) -> dict:
    """Append an approved job discovery to the overlay (id/URL dedup enforced)."""
    existing = load_approved_job_discoveries()
    official_url = item.get("official_pdf_url") or item.get("source_url")
    if any(
        exam.get("id") == item.get("id")
        or ((exam.get("official_pdf_url") or exam.get("source_url")) == official_url and official_url)
        for exam in existing + _BASE_SEED_EXAMS
    ):
        raise ValueError("approved job discovery duplicates an existing seed id or official URL")
    serializable = {
        key: (value.isoformat() if isinstance(value, date)
              else sorted(value) if isinstance(value, set) else value)
        for key, value in item.items()
    }
    existing.append(serializable)
    APPROVED_JOB_SEED_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = APPROVED_JOB_SEED_PATH.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(existing, indent=2, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, APPROVED_JOB_SEED_PATH)
    refresh_approved_job_discoveries()
    return item


def refresh_approved_job_discoveries() -> None:
    approved = load_approved_job_discoveries()
    known = {exam["id"] for exam in SEED_EXAMS}
    for item in approved:
        if item.get("id") not in known:
            SEED_EXAMS.append(item)
            known.add(item["id"])


SEED_EXAMS: list[dict] = _BASE_SEED_EXAMS + load_approved_job_discoveries()


# Fields the curated seed file is allowed to refresh on existing seed rows.
# Content fields (title, ages, degrees, topics, organizing_body…) are never
# overwritten — admins may edit those in place.
_REFRESHABLE_FIELDS = (
    "notification_date",
    "application_deadline",
    "exam_date",
    "source_url",
    "apply_url",
    "last_checked_at",
    "verified_on",
    "verification_status",
)

# Every seeded notification must expose provenance. The PDF/homepage URL is the
# best available source for the seed rows; `last_checked_at` is the day the seed
# data was loaded. `verification_status` starts as "check_required" — a row is
# only "verified" once its deadline has been confirmed against an official
# source (see docs/SEED_VERIFICATION_*.md).
for _seed_exam in SEED_EXAMS:
    _seed_exam.setdefault("source_url", _seed_exam.get("official_pdf_url"))
    _seed_exam.setdefault("last_checked_at", date.today())
    _seed_exam.setdefault("verified_on", None)
    _seed_exam.setdefault("verification_status", "check_required")


async def upsert_seed_exams(db) -> int:
    """Idempotent startup seed.

    Inserts missing rows (never overwriting anything), and refreshes only the
    provenance/deadline fields on existing seed rows:

    * verification metadata and provenance are kept current from the file;
    * if a seed row's deadline moved forward (a government deadline was
      extended), the refreshed row is reopened even if the expiry job had
      deactivated it — that is how extended notifications come back to life;
    * admin edits and intentional deactivations without a date change are
      preserved.

    Returns the number of rows inserted.
    """
    from sqlalchemy import select

    from app.core.timeutils import today_ist
    from app.models.exam import ExamNotification

    existing_rows = {
        row.id: row
        for row in (await db.execute(select(ExamNotification))).scalars().all()
    }
    inserted = 0
    refreshed = 0
    for item in SEED_EXAMS:
        row = existing_rows.get(item["id"])
        if row is None:
            payload = {k: (list(v) if k == "topics" else v) for k, v in item.items()}
            db.add(ExamNotification(**payload))
            inserted += 1
            continue

        changed = False
        # A deadline confirmed against the official PDF by the jobs watchdog
        # is authoritative: the curated file must not silently undo it on the
        # next startup. Other provenance fields still refresh normally.
        deadline_locked = bool(getattr(row, "deadline_locked", False))
        locked_fields = {
            "application_deadline", "exam_date", "verified_on",
            "verification_status", "source_url", "last_checked_at",
        } if deadline_locked else set()
        new_deadline = item.get("application_deadline")
        today = today_ist()
        if (
            not deadline_locked
            and new_deadline is not None
            and row.application_deadline is not None
            and new_deadline > row.application_deadline
        ):
            # Extension detected: bring the row back only if the new window is
            # actually open — a forward move that is still in the past does not.
            if not row.is_active and new_deadline >= today:
                logger.info(
                    "reopening seed exam %r — application_deadline extended %s → %s",
                    row.id, row.application_deadline, new_deadline,
                )
                row.is_active = True
            changed = True
        for field in _REFRESHABLE_FIELDS:
            if field in locked_fields:
                continue
            if field == "apply_url" and "apply_url" not in item:
                # Never null out a stored apply link the file does not define —
                # rows may have gotten one from the pipeline or an admin.
                continue
            value = item.get(field)
            if value != getattr(row, field):
                setattr(row, field, value)
                changed = True
        if changed:
            refreshed += 1
    if inserted or refreshed:
        await db.commit()
    if refreshed:
        logger.info("refreshed provenance for %d seed exam rows", refreshed)
    return inserted
