from datetime import date

SEED_EXAMS = [
    # ==================== 10TH & 12TH PASS GOVERNMENT JOBS ====================
    {
        "id": "ssc-chsl-12th",
        "title": "SSC Combined Higher Secondary Level (CHSL)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Clerical / Intermediate",
        "notification_date": date(2026, 7, 1),
        "application_deadline": date(2026, 12, 30),
        "exam_date": date(2027, 2, 20),
        "official_pdf_url": "https://ssc.gov.in/",
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
        "notification_date": date(2026, 10, 1),
        "application_deadline": date(2026, 12, 10),
        "exam_date": date(2027, 4, 18),
        "official_pdf_url": "https://upsc.gov.in/",
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
        "notification_date": date(2026, 9, 20),
        "application_deadline": date(2026, 12, 15),
        "exam_date": date(2027, 3, 12),
        "official_pdf_url": "https://www.rrbcdg.gov.in/",
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
        "notification_date": date(2026, 8, 15),
        "application_deadline": date(2026, 12, 10),
        "exam_date": date(2027, 2, 25),
        "official_pdf_url": "https://ssc.gov.in/",
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
        "notification_date": date(2026, 9, 5),
        "application_deadline": date(2026, 12, 31),
        "exam_date": date(2027, 2, 15),
        "official_pdf_url": "https://ssc.gov.in/",
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
        "notification_date": date(2026, 8, 20),
        "application_deadline": date(2026, 12, 20),
        "exam_date": date(2027, 1, 28),
        "official_pdf_url": "https://delhipolice.gov.in/",
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
        "notification_date": date(2026, 6, 15),
        "application_deadline": date(2026, 12, 15),
        "exam_date": date(2027, 2, 10),
        "official_pdf_url": "https://ssc.gov.in/",
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
        "notification_date": date(2026, 9, 1),
        "application_deadline": date(2026, 11, 30),
        "exam_date": date(2027, 3, 5),
        "official_pdf_url": "https://www.rrbcdg.gov.in/",
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
        "notification_date": date(2026, 8, 1),
        "application_deadline": date(2026, 11, 25),
        "exam_date": date(2027, 1, 24),
        "official_pdf_url": "https://www.ibps.in/",
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
        "notification_date": date(2026, 10, 10),
        "application_deadline": date(2026, 12, 20),
        "exam_date": date(2027, 2, 28),
        "official_pdf_url": "https://calicut.nielit.in/nic/",
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
        "notification_date": date(2026, 9, 15),
        "application_deadline": date(2026, 12, 5),
        "exam_date": date(2027, 1, 18),
        "official_pdf_url": "https://sbi.co.in/web/careers",
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
        "notification_date": date(2026, 10, 1),
        "application_deadline": date(2026, 12, 18),
        "exam_date": date(2027, 2, 14),
        "official_pdf_url": "https://www.mha.gov.in/",
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
        "notification_date": date(2027, 2, 1),
        "application_deadline": date(2027, 2, 21),
        "exam_date": date(2027, 5, 25),
        "official_pdf_url": "https://upsc.gov.in/",
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
        "notification_date": date(2026, 10, 20),
        "application_deadline": date(2026, 12, 28),
        "exam_date": date(2027, 3, 20),
        "official_pdf_url": "https://rac.gov.in/",
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
    }
]