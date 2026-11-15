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
    },

    # ==================== 10TH & 12TH PASS / DIPLOMA JOBS (EXPANDED) ====================
    {
        "id": "ssc-stenographer-12th",
        "title": "SSC Stenographer (Grade C & D)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Clerical / Typing & Shorthand",
        "notification_date": date(2026, 10, 20),
        "application_deadline": date(2026, 12, 2),
        "exam_date": date(2027, 3, 10),
        "official_pdf_url": "https://ssc.gov.in/",
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
        "notification_date": date(2026, 11, 1),
        "application_deadline": date(2026, 12, 31),
        "exam_date": date(2027, 5, 15),
        "official_pdf_url": "https://joinindianarmy.nic.in/",
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
        "notification_date": date(2026, 10, 15),
        "application_deadline": date(2026, 12, 12),
        "exam_date": date(2027, 3, 28),
        "official_pdf_url": "https://agniveervayu.cdac.in/",
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
        "notification_date": date(2026, 11, 5),
        "application_deadline": date(2026, 12, 8),
        "exam_date": date(2027, 5, 20),
        "official_pdf_url": "https://www.joinindiannavy.gov.in/",
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
        "notification_date": date(2026, 11, 5),
        "application_deadline": date(2026, 12, 8),
        "exam_date": date(2027, 5, 22),
        "official_pdf_url": "https://www.joinindiannavy.gov.in/",
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
        "notification_date": date(2026, 11, 1),
        "application_deadline": date(2027, 1, 15),
        "exam_date": date(2027, 6, 10),
        "official_pdf_url": "https://joinindianarmy.nic.in/",
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
        "notification_date": date(2026, 11, 10),
        "application_deadline": date(2027, 1, 15),
        "exam_date": date(2027, 5, 5),
        "official_pdf_url": "https://www.rrbcdg.gov.in/",
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
        "notification_date": date(2026, 11, 15),
        "application_deadline": date(2027, 1, 20),
        "exam_date": date(2027, 6, 12),
        "official_pdf_url": "https://www.rrbcdg.gov.in/",
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
        "notification_date": date(2026, 11, 20),
        "application_deadline": date(2027, 1, 12),
        "exam_date": date(2027, 6, 20),
        "official_pdf_url": "https://ssc.gov.in/",
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
        "notification_date": date(2026, 11, 12),
        "application_deadline": date(2027, 1, 25),
        "exam_date": date(2027, 6, 8),
        "official_pdf_url": "https://www.rrbcdg.gov.in/",
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
        "notification_date": date(2026, 10, 1),
        "application_deadline": date(2026, 12, 1),
        "exam_date": date(2027, 1, 9),
        "official_pdf_url": "https://www.ibps.in/",
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
        "notification_date": date(2026, 10, 5),
        "application_deadline": date(2026, 12, 8),
        "exam_date": date(2027, 1, 10),
        "official_pdf_url": "https://www.ibps.in/",
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
        "notification_date": date(2026, 10, 8),
        "application_deadline": date(2026, 12, 4),
        "exam_date": date(2027, 1, 17),
        "official_pdf_url": "https://sbi.co.in/web/careers",
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
        "notification_date": date(2026, 11, 1),
        "application_deadline": date(2026, 12, 20),
        "exam_date": date(2027, 2, 6),
        "official_pdf_url": "https://www.ibps.in/",
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
        "notification_date": date(2026, 11, 1),
        "application_deadline": date(2026, 12, 20),
        "exam_date": date(2027, 2, 7),
        "official_pdf_url": "https://www.ibps.in/",
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
        "notification_date": date(2026, 12, 1),
        "application_deadline": date(2027, 1, 5),
        "exam_date": date(2027, 3, 15),
        "official_pdf_url": "https://www.rbi.org.in/",
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
        "notification_date": date(2027, 2, 10),
        "application_deadline": date(2027, 3, 8),
        "exam_date": date(2027, 6, 5),
        "official_pdf_url": "https://www.rbi.org.in/",
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
        "notification_date": date(2026, 12, 5),
        "application_deadline": date(2027, 1, 10),
        "exam_date": date(2027, 3, 28),
        "official_pdf_url": "https://www.nabard.org/",
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
        "notification_date": date(2026, 10, 25),
        "application_deadline": date(2026, 12, 12),
        "exam_date": date(2027, 2, 20),
        "official_pdf_url": "https://www.licindia.in/",
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
        "title": "EPFO Enforcement Officer / Accounts Officer (via SSC)",
        "organizing_body": "Staff Selection Commission (SSC)",
        "post_type": "Central Govt / Statutory Body",
        "notification_date": date(2026, 12, 1),
        "application_deadline": date(2027, 1, 18),
        "exam_date": date(2027, 4, 10),
        "official_pdf_url": "https://ssc.gov.in/",
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
        "notification_date": date(2026, 12, 1),
        "application_deadline": date(2027, 1, 10),
        "exam_date": date(2027, 4, 15),
        "official_pdf_url": "https://ssc.gov.in/",
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
        "notification_date": date(2027, 4, 1),
        "application_deadline": date(2027, 4, 25),
        "exam_date": date(2027, 8, 1),
        "official_pdf_url": "https://upsc.gov.in/",
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
        "notification_date": date(2026, 12, 15),
        "application_deadline": date(2027, 1, 5),
        "exam_date": date(2027, 4, 18),
        "official_pdf_url": "https://upsc.gov.in/",
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
        "notification_date": date(2026, 10, 1),
        "application_deadline": date(2026, 12, 5),
        "exam_date": date(2027, 6, 20),
        "official_pdf_url": "https://upsc.gov.in/",
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
        "notification_date": date(2026, 11, 1),
        "application_deadline": date(2026, 12, 11),
        "exam_date": date(2027, 1, 30),
        "official_pdf_url": "https://afcat.cdac.in/",
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
        "notification_date": date(2027, 2, 10),
        "application_deadline": date(2027, 3, 10),
        "exam_date": date(2027, 6, 15),
        "official_pdf_url": "https://upsc.gov.in/",
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
        "title": "ISRO Scientist / Engineer-B",
        "organizing_body": "Indian Space Research Organisation (ISRO)",
        "post_type": "Technical / Space Research",
        "notification_date": date(2026, 11, 20),
        "application_deadline": date(2027, 1, 30),
        "exam_date": date(2027, 3, 15),
        "official_pdf_url": "https://www.isro.gov.in/",
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
        "notification_date": date(2026, 12, 10),
        "application_deadline": date(2027, 1, 25),
        "exam_date": date(2027, 3, 30),
        "official_pdf_url": "https://www.iocl.com/",
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
        "notification_date": date(2026, 12, 15),
        "application_deadline": date(2027, 2, 10),
        "exam_date": date(2027, 4, 25),
        "official_pdf_url": "https://www.ntpc.co.in/",
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
        "notification_date": date(2027, 1, 10),
        "application_deadline": date(2027, 2, 10),
        "exam_date": date(2027, 6, 25),
        "official_pdf_url": "https://www.bsnl.co.in/",
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
    {
        "id": "kvs-tgt",
        "title": "KVS Trained Graduate Teacher (TGT) / PGT",
        "organizing_body": "Kendriya Vidyalaya Sangathan (KVS)",
        "post_type": "Teaching / Central Schools",
        "notification_date": date(2026, 12, 5),
        "application_deadline": date(2027, 1, 5),
        "exam_date": date(2027, 5, 2),
        "official_pdf_url": "https://kvsangathan.nic.in/",
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
    }
]

# Every seeded notification must expose provenance. The PDF/homepage URL is the
# best available source for the seed rows; `last_checked_at` is the day the seed
# data was loaded, not a claim that the notification is still live.
for _seed_exam in SEED_EXAMS:
    _seed_exam.setdefault("source_url", _seed_exam.get("official_pdf_url"))
    _seed_exam.setdefault("last_checked_at", date.today())

async def upsert_seed_exams(db) -> int:
    """Idempotent startup seed. Insert SEED_EXAMS rows that are missing;
    never overwrite existing rows (the API may retire or edit them). Returns
    the number of rows inserted."""
    from sqlalchemy import select

    from app.models.exam import ExamNotification

    existing = set((await db.execute(select(ExamNotification.id))).scalars().all())
    inserted = 0
    for item in SEED_EXAMS:
        if item["id"] in existing:
            continue
        payload = {k: (list(v) if k == "topics" else v) for k, v in item.items()}
        db.add(ExamNotification(**payload))
        inserted += 1
    if inserted:
        await db.commit()
    return inserted
