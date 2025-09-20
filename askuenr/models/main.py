from django.db import models
from django.contrib.auth.models import User # Import Django's built-in User model for staff/student accounts


class University(models.Model):
    """
    Represents the University of Energy and Natural Resources (UENR) itself.
    Stores general information about the institution.
    """
    name = models.CharField(max_length=255, default="University of Energy and Natural Resources")
    motto = models.CharField(max_length=255, blank=True, null=True)
    history = models.TextField(
        help_text="A brief history of UENR, including its establishment and key milestones."
    )
    vision = models.TextField(blank=True, null=True)
    mission = models.TextField(blank=True, null=True)
    core_values = models.TextField(blank=True, null=True)
    established_date = models.DateField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    # New fields for University
    accreditation_status = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Fully Accredited, Provisional")
    national_ranking = models.IntegerField(blank=True, null=True)
    international_ranking = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., QS World Ranking, Times Higher Education")
    
    chancellor = models.OneToOneField(
        'StaffProfile',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='chancellor_of_university',
        help_text="The current Chancellor of the University."
    )

    vice_chancellor = models.OneToOneField(
        'StaffProfile',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='vice_chancellor_of_university',
        help_text="The current Vice-Chancellor of the University."
    )

    dean = models.OneToOneField(
        'StaffProfile',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='dean_of_student',
        help_text="The current Chancellor of the University."
    )
    

    class Meta:
        verbose_name_plural = "University Information"

    def __str__(self):
        return self.name

class Campus(models.Model):
    """
    Represents a physical campus location of UENR.
    """
    name = models.CharField(max_length=255, unique=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='campuses')
    location_address = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    # Add coordinates if you plan to integrate maps
    latitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)

    class Meta:
        verbose_name_plural = "Campuses"
        ordering = ['name']

    def __str__(self):
        return self.name

class School(models.Model):
    """
    Represents an academic school within UENR (e.g., School of Engineering).
    """
    name = models.CharField(max_length=255, unique=True)
    university = models.ForeignKey(University, on_delete=models.CASCADE, related_name='schools')
    dean = models.OneToOneField(
        'StaffProfile',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='dean_of_school',
        help_text="The Dean of this School."
    )
    description = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    # New field for School
    campus = models.ForeignKey(Campus, on_delete=models.SET_NULL, blank=True, null=True, related_name='schools_on_campus')

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

class Department(models.Model):
    """
    Represents an academic department within a School (e.g., Computer Science and Informatics).
    """
    name = models.CharField(max_length=255, unique=True)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='departments')
    head_of_department = models.OneToOneField(
        'StaffProfile',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='hod_of_department',
        help_text="The Head of this Department."
    )
    description = models.TextField(blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    # New field for Department
    office_location = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.school.name})"

# --- People (Staff only) ---

class StaffProfile(models.Model):
    """
    Represents a profile for university staff, including lecturers and administrative personnel.
    """
  
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    title = models.CharField(
        max_length=50,
        choices=[
            ('Prof.', 'Professor'),
            ('Dr.', 'Doctor'),
            ('Mr.', 'Mr.'),
            ('Ms.', 'Ms.'),
            ('Mrs.', 'Mrs.'),
        ],
        blank=True,
        null=True
    )
    position = models.CharField(
        max_length=100,
        choices=[
            ('C', 'Chancellor'),
            ('VC', 'Vice-Chancellor'),
            ('Pro-VC', 'Pro Vice-Chancellor'),
            ('Registrar', 'Registrar'),
            ('Lecturer', 'Lecturer'),
            ('Src', 'Src'),
            ('Snr. Lecturer', 'Senior Lecturer'),
            ('Assoc. Prof.', 'Associate Professor'),
            ('Admin Staff', 'Administrative Staff'),
            ('Other', 'Other Staff'),
        ]
    )
    
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='staff_members'
    )
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    bio = models.TextField(blank=True, null=True, help_text="A short biography or professional summary.")
    research_interests = models.TextField(blank=True, null=True)
    is_hod = models.BooleanField(default=False, help_text="Is this staff member a Head of Department?")
    is_dean = models.BooleanField(default=False, help_text="Is this staff member a Dean of a School?")
    is_admin_staff = models.BooleanField(default=False, help_text="Is this staff member part of the central administration (e.g., Registrar's Office, VC's Office)?")
    profile_picture = models.ImageField(upload_to='staff_profiles/', blank=True, null=True)
    # New fields for StaffProfile
    academic_qualifications = models.TextField(blank=True, null=True, help_text="Degrees, institutions, and years.")
    office_location = models.CharField(max_length=255, blank=True, null=True)
    office_hours = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., Mon-Fri, 9 AM - 4 PM")
    google_scholar_url = models.URLField(blank=True, null=True)
    researchgate_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Staff Profiles"
        ordering = ['last_name', 'first_name']

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}"
        if self.title:
            return f"{self.title} {full_name} ({self.position})"
        return f"{full_name} ({self.position})"

# --- Academic Information ---

class Program(models.Model):
    """
    Represents an academic program offered by UENR (e.g., BSc. Computer Science).
    """
    PROGRAM_TYPES = [
        ('Diploma', 'Diploma'),
        ('Undergraduate', 'Undergraduate'),
        ('Postgraduate', 'Postgraduate'),
        ('PhD', 'PhD'),
    ]

    name = models.CharField(max_length=255, unique=True)
    program_type = models.CharField(max_length=20, choices=PROGRAM_TYPES)
    school = models.ForeignKey(School, on_delete=models.CASCADE, related_name='programs')
    department = models.ForeignKey(
        Department,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='offered_programs',
        help_text="The primary department offering this program (can be multidisciplinary)."
    )
    duration_years = models.IntegerField(help_text="Duration of the program in years.")
    description = models.TextField(blank=True, null=True)
    admission_requirements = models.TextField(
        help_text="Detailed admission requirements (e.g., WASSCE aggregates, specific subjects)."
    )
    career_prospects = models.TextField(blank=True, null=True)
    # New fields for Program
    accreditation_status = models.CharField(max_length=100, blank=True, null=True, help_text="e.g., Accredited by NAB, Professional Body Accreditation")
    program_coordinator = models.ForeignKey(
        'StaffProfile',
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='coordinated_programs',
        help_text="The staff member responsible for coordinating this program."
    )
    # Structured admission requirements
    min_wassce_aggregate = models.IntegerField(blank=True, null=True)
    required_core_subjects = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated list, e.g., English, Mathematics, Integrated Science")
    required_elective_subjects = models.CharField(max_length=255, blank=True, null=True, help_text="Comma-separated list, e.g., Physics, Chemistry, Elective Mathematics")

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.program_type})"

class Course(models.Model):
    """
    Represents an individual course offered within a program.
    """
    SEMESTER_CHOICES = [
        ('Harmattan', 'Harmattan Semester'),
        ('Rain', 'Rain Semester'),
        ('Both', 'Both Semesters'),
        ('Other', 'Other (e.g., Summer Session)'),
    ]

    code = models.CharField(max_length=20, unique=True, help_text="e.g., CS 101, MECH 203")
    title = models.CharField(max_length=255)
    credit_hours = models.DecimalField(max_digits=3, decimal_places=1)
    description = models.TextField(blank=True, null=True)
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='courses')
    programs = models.ManyToManyField(Program, related_name='courses')
    semester_offered = models.CharField(max_length=20, choices=SEMESTER_CHOICES, blank=True, null=True)
    lecturers = models.ManyToManyField(StaffProfile, related_name='taught_courses', blank=True)
    # New fields for Course
    prerequisites = models.ManyToManyField('self', symmetrical=False, blank=True, related_name='required_for', help_text="Other courses required before taking this one.")
    learning_outcomes = models.TextField(blank=True, null=True)
    course_materials_url = models.URLField(blank=True, null=True)

    class Meta:
        ordering = ['code']

    def __str__(self):
        return f"{self.code}: {self.title}"


class GPA(models.Model):
    lower_bound = models.IntegerField(
        null=True, blank=True,
        help_text="Lower bound of the score range (inclusive), e.g. 80"
    )
    upper_bound = models.IntegerField(
        null=True, blank=True,
        help_text="Upper bound of the score range (inclusive), e.g. 100"
    )
    letter_grade = models.CharField(
        null=True, blank=True,
        max_length=2,
        help_text="Letter grade, e.g. A, B+, C+"
    )
    grade_point = models.DecimalField(
        null=True, blank=True,
        max_digits=4,
        decimal_places=2,
        help_text="Grade point equivalent, e.g. 4.00"
    )
    interpretation = models.CharField(
        null=True, blank=True,
        max_length=50,
        help_text="Interpretation of the grade, e.g. Excellent, Good"
    )
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "GPAs"
        ordering = ['-upper_bound']

    def __str__(self):
        return f"{self.letter_grade} ({self.lower_bound}-{self.upper_bound}%) - GP {self.grade_point}"


class AcademicRecord(models.Model):
    """
    Represents academic records without student association.
    """
    course = models.ForeignKey(
        'Course',
        on_delete=models.CASCADE
    )
    academic_year = models.CharField(
        max_length=9,
        help_text="e.g., 2023/2024"
    )
    semester = models.CharField(
        max_length=20,
        choices=[
            ('Harmattan', 'Harmattan Semester'),
            ('Rain', 'Rain Semester'),
            ('Summer', 'Summer Session'),
        ]
    )
    raw_score = models.IntegerField(
        blank=True, null=True,
        help_text="Score out of 100"
    )

    # New relationship to GPA table
    gpa = models.ForeignKey(
        GPA,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Linked GPA record based on the raw score."
    )

    # Optionally keep these for denormalization or fast querying
    grade = models.CharField(
        max_length=5,
        blank=True,
        null=True,
        help_text="e.g., A, B+, C, F"
    )
    grade_point = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        blank=True,
        null=True,
        help_text="Grade point on a 4.0 scale"
    )

    class Meta:
        verbose_name_plural = "Academic Records"
        ordering = ['academic_year', 'semester', 'course']

    def __str__(self):
        return f"{self.course.code} ({self.academic_year} {self.semester})"

    def save(self, *args, **kwargs):
        """
        Optionally auto-assign the GPA foreign key based on raw_score.
        """
        if self.raw_score is not None:
            matched_gpa = GPA.objects.filter(
                lower_bound__lte=self.raw_score,
                upper_bound__gte=self.raw_score
            ).first()
            if matched_gpa:
                self.gpa = matched_gpa
                self.grade = matched_gpa.letter_grade
                self.grade_point = matched_gpa.grade_point
        super().save(*args, **kwargs)



class CampusService(models.Model):
    """
    Information about various services available on campus.
    """
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    contact_info = models.TextField(blank=True, null=True, help_text="Phone numbers, emails, office hours, etc.")
    location = models.CharField(max_length=255, blank=True, null=True, help_text="Physical location on campus.")
    operating_hours = models.CharField(max_length=255, blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    # New fields for CampusService
    service_category = models.CharField(
        max_length=100,
        choices=[
            ('Academic Support', 'Academic Support'),
            ('Student Life', 'Student Life'),
            ('Health & Wellness', 'Health & Wellness'),
            ('Administrative', 'Administrative'),
            ('IT Support', 'IT Support'),
            ('Facilities', 'Facilities'),
            ('Other', 'Other'),
        ],
        blank=True,
        null=True
    )
    service_manager = models.ForeignKey(
        StaffProfile,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name='managed_services',
        help_text="The staff member responsible for this service."
    )

    class Meta:
        verbose_name_plural = "Campus Services"
        ordering = ['name']

    def __str__(self):
        return self.name

class FeeStructure(models.Model):
    """
    Details about university fees for different programs and academic years.
    """
    FEE_TYPES = [
        ('Tuition', 'Tuition Fee'),
        ('Accommodation', 'Accommodation Fee'),
        ('Examination', 'Examination Fee'),
        ('Other', 'Other Fee'),
        ('Application', 'Application Fee'),
        ('Graduation', 'Graduation Fee'),
    ]

    fee_type = models.CharField(max_length=50, choices=FEE_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    academic_year = models.CharField(max_length=9, help_text="e.g., 2024/2025")
    program = models.ForeignKey(Program, on_delete=models.SET_NULL, blank=True, null=True, related_name='fees')
    notes = models.TextField(blank=True, null=True, help_text="Payment deadlines, installment options, etc.")
    # New fields for FeeStructure
    currency = models.CharField(max_length=10, default='GHS', help_text="Currency of the fee, e.g., GHS, USD")
    payment_methods = models.TextField(blank=True, null=True, help_text="Accepted payment methods, e.g., Bank Transfer, Mobile Money")
    is_refundable = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Fee Structures"
        unique_together = ('fee_type', 'academic_year', 'program') # Ensure unique fee entries
        ordering = ['academic_year', 'fee_type']

    def __str__(self):
        program_name = self.program.name if self.program else "General"
        return f"{self.fee_type} for {program_name} ({self.academic_year}): {self.currency} {self.amount}"

class NewsAndAnnouncement(models.Model):
    """
    For university news, updates, and important announcements.
    """
    TARGET_AUDIENCES = [
        ('All', 'All Users'),
        ('Students', 'Current Students'),
        ('Staff', 'Staff Members'),
        ('Prospective', 'Prospective Applicants'),
        ('Alumni', 'Alumni'),
    ]
    CATEGORY_CHOICES = [
        ('Admissions', 'Admissions'),
        ('Events', 'Events'),
        ('Policy', 'Policy Updates'),
        ('Academic', 'Academic Information'),
        ('General', 'General News'),
        ('Scholarship', 'Scholarship Opportunity'),
        ('Research', 'Research News'),
    ]

    title = models.CharField(max_length=255)
    content = models.TextField()
    publish_date = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    target_audience = models.CharField(max_length=20, choices=TARGET_AUDIENCES, default='All')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='General')
    author = models.ForeignKey(StaffProfile, on_delete=models.SET_NULL, blank=True, null=True, related_name='authored_news')
    attachment = models.FileField(upload_to='news_attachments/', blank=True, null=True)
    # New field for NewsAndAnnouncement
    event_date_time = models.DateTimeField(blank=True, null=True, help_text="For event-related announcements.")
    external_link = models.URLField(blank=True, null=True, help_text="Link to the full article or external resource.")

    class Meta:
        verbose_name_plural = "News and Announcements"
        ordering = ['-publish_date'] # Order by most recent first

    def __str__(self):
        return f"{self.title} ({self.publish_date.strftime('%Y-%m-%d')})"

class Event(models.Model):
    """
    Represents a specific event happening at UENR.
    """
    EVENT_TYPES = [
        ('Academic', 'Academic Event'),
        ('Social', 'Social Event'),
        ('Sports', 'Sports Event'),
        ('Cultural', 'Cultural Event'),
        ('Workshop', 'Workshop/Seminar'),
        ('Public Lecture', 'Public Lecture'),
        ('Other', 'Other'),
    ]
    name = models.CharField(max_length=255)
    description = models.TextField()
    start_date_time = models.DateTimeField()
    end_date_time = models.DateTimeField(blank=True, null=True)
    location = models.CharField(max_length=255, help_text="e.g., Auditorium, Specific Lecture Hall, Online")
    event_type = models.CharField(max_length=50, choices=EVENT_TYPES, default='Other')
    organizer = models.CharField(max_length=255, blank=True, null=True, help_text="Department, Club, Office, etc.")
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)
    registration_link = models.URLField(blank=True, null=True)
    is_public = models.BooleanField(default=True, help_text="Is this event open to the general public?")
    image = models.ImageField(upload_to='event_images/', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Events"
        ordering = ['start_date_time']

    def __str__(self):
        return f"{self.name} on {self.start_date_time.strftime('%Y-%m-%d %H:%M')}"

class Scholarship(models.Model):
    """
    Details about available scholarships for UENR students.
    """
    SCHOLARSHIP_TYPES = [
        ('Merit-based', 'Merit-based'),
        ('Need-based', 'Need-based'),
        ('Research', 'Research Scholarship'),
        ('International', 'International Scholarship'),
        ('Departmental', 'Departmental Scholarship'),
        ('Other', 'Other'),
    ]
    name = models.CharField(max_length=255)
    description = models.TextField()
    scholarship_type = models.CharField(max_length=50, choices=SCHOLARSHIP_TYPES)
    eligibility_criteria = models.TextField(help_text="Who can apply? GPA, program, nationality, etc.")
    application_deadline = models.DateField(blank=True, null=True)
    amount_or_benefits = models.CharField(max_length=255, blank=True, null=True, help_text="e.g., Full tuition, GHS 5000, Accommodation")
    application_link = models.URLField(blank=True, null=True)
    contact_info = models.TextField(blank=True, null=True, help_text="Email or phone for inquiries.")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Scholarships"
        ordering = ['-is_active', 'application_deadline']

    def __str__(self):
        return self.name

class FAQ(models.Model):
    """
    A model for frequently asked questions and their answers.
    This is crucial for AskUner's direct knowledge base.
    """
    QUESTION_CATEGORIES = [
        ('Admissions', 'Admissions'),
        ('Academics', 'Academics'),
        ('Fees & Financial Aid', 'Fees & Financial Aid'),
        ('Campus Life', 'Campus Life'),
        ('IT Support', 'IT Support'),
        ('Services', 'Services'),
        ('General', 'General Information'),
    ]
    question = models.TextField(unique=True)
    answer = models.TextField()
    category = models.CharField(max_length=100, choices=QUESTION_CATEGORIES, default='General')
    related_programs = models.ManyToManyField(Program, blank=True, related_name='faqs')
    related_departments = models.ManyToManyField(Department, blank=True, related_name='faqs')
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "FAQs"
        ordering = ['category', 'question']

    def __str__(self):
        return self.question[:75] + '...' if len(self.question) > 75 else self.question

class ContactInfo(models.Model):
    """
    General contact information for various university offices/entities.
    """
    CONTACT_TYPES = [
        ('Admissions', 'Admissions Office'),
        ('Registrar', 'Registrar\'s Office'),
        ('Finance', 'Finance Directorate'),
        ('IT Helpdesk', 'IT Helpdesk'),
        ('Health Services', 'Health Services'),
        ('Security', 'Security Office'),
        ('General Enquiries', 'General Enquiries'),
        ('Other', 'Other'),
    ]
    entity_name = models.CharField(max_length=255, help_text="e.g., Admissions Office, Main Switchboard")
    contact_type = models.CharField(max_length=50, choices=CONTACT_TYPES, default='General Enquiries')
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    physical_address = models.TextField(blank=True, null=True)
    operating_hours = models.CharField(max_length=255, blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)

    class Meta:
        verbose_name_plural = "Contact Information"
        ordering = ['entity_name']

    def __str__(self):
        return f"{self.entity_name} ({self.contact_type})"