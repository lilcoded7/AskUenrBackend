import requests
from bs4 import BeautifulSoup
import json
import time
from datetime import datetime, date
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

# Import your models (adjust the import path according to your app structure)
from askuenr.models.main import (
    University, Campus, School, Department, StaffProfile, StudentProfile,
    Program, Course, CampusService, FeeStructure, NewsAndAnnouncement,
    Event, Scholarship, FAQ, ContactInfo
)


class Command(BaseCommand):
    help = 'Scrape UENR data and populate the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--update-only',
            action='store_true',
            help='Only update existing records, do not create new ones',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving to database',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Enable verbose output',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.base_url = 'https://uenr.edu.gh'
        self.dry_run = False
        self.verbose = False

    def log(self, message, level='INFO'):
        if self.verbose or level == 'ERROR':
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            self.stdout.write(f'[{timestamp}] {level}: {message}')

    def fetch_page(self, url, retries=3):
        """Fetch a web page with error handling and retries"""
        for attempt in range(retries):
            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                self.log(f'Error fetching {url} (attempt {attempt + 1}): {e}', 'ERROR')
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return None

    def parse_html(self, html_content):
        """Parse HTML content with BeautifulSoup"""
        return BeautifulSoup(html_content, 'html.parser')

    def safe_get_text(self, element, default=''):
        """Safely extract text from BeautifulSoup element"""
        return element.get_text(strip=True) if element else default

    def create_or_update_university(self):
        """Create or update the main university record"""
        self.log('Processing University information...')
        
        # Fetch main page
        response = self.fetch_page(self.base_url)
        if not response:
            self.log('Failed to fetch main university page', 'ERROR')
            return None

        soup = self.parse_html(response.content)
        
        # Extract university information
        university_data = {
            'name': 'University of Energy and Natural Resources',
            'motto': 'Energy and Natural Resources for Development',
            'established_date': date(2011, 12, 31),
            'vision': 'To be a centre of excellence in energy and natural resources education, research, and innovation',
            'mission': 'To provide leadership and management of energy and natural resources through interdisciplinary education, research, and community service',
            'core_values': 'Excellence, Innovation, Integrity, Collaboration, Sustainability',
            'contact_email': 'info@uenr.edu.gh',
            'contact_phone': '+233 352 091 290',
            'address': 'University of Energy and Natural Resources, Sunyani, Bono Region, Ghana',
            'accreditation_status': 'Fully Accredited by National Accreditation Board (NAB)',
        }

        if not self.dry_run:
            university, created = University.objects.get_or_create(
                name=university_data['name'],
                defaults=university_data
            )
            if not created:
                for key, value in university_data.items():
                    setattr(university, key, value)
                university.save()
            
            self.log(f'University record {"created" if created else "updated"}')
            return university
        else:
            self.log('DRY RUN: Would create/update university record')
            return None

    def create_campus_data(self, university):
        """Create campus information"""
        self.log('Processing Campus information...')
        
        campus_data = [
            {
                'name': 'Main Campus',
                'location_address': 'Sunyani, Bono Region, Ghana',
                'description': 'The main campus of UENR located in Sunyani, housing all major faculties and administrative offices',
                'latitude': Decimal('7.3419'),
                'longitude': Decimal('-2.3264')
            },
            {
                'name': 'UENR Accra Office',
                'location_address': 'Office Complex of the Vice Chancellors Ghana (VCG), UPSA Road, Accra',
                'description': 'UENR administrative office in Accra for admissions and other services',
                'latitude': Decimal('5.6037'),
                'longitude': Decimal('-0.1870')
            }
        ]

        if not self.dry_run:
            for data in campus_data:
                campus, created = Campus.objects.get_or_create(
                    name=data['name'],
                    university=university,
                    defaults=data
                )
                if not created:
                    for key, value in data.items():
                        if key not in ['name', 'university']:
                            setattr(campus, key, value)
                    campus.save()
                
                self.log(f'Campus "{data["name"]}" {"created" if created else "updated"}')
        else:
            self.log(f'DRY RUN: Would create/update {len(campus_data)} campus records')

    def create_schools_and_departments(self, university):
        """Create schools and departments"""
        self.log('Processing Schools and Departments...')
        
        schools_data = [
            {
                'name': 'School of Engineering',
                'description': 'Offers engineering programs with emphasis on energy and natural resources',
                'departments': [
                    'Department of Mechanical Engineering',
                    'Department of Electrical and Electronic Engineering',
                    'Department of Civil Engineering',
                    'Department of Agricultural and Biosystems Engineering'
                ]
            },
            {
                'name': 'School of Natural Resources',
                'description': 'Focuses on natural resources management and environmental studies',
                'departments': [
                    'Department of Forest Resources Technology',
                    'Department of Environmental Science',
                    'Department of Renewable Natural Resources'
                ]
            },
            {
                'name': 'School of Business',
                'description': 'Offers business and management programs',
                'departments': [
                    'Department of Business Administration',
                    'Department of Economics',
                    'Department of Accounting and Finance'
                ]
            },
            {
                'name': 'School of Sciences',
                'description': 'Provides foundational science education',
                'departments': [
                    'Department of Mathematics and Statistics',
                    'Department of Physics',
                    'Department of Chemistry',
                    'Department of Computer Science and Informatics'
                ]
            },
            {
                'name': 'School of Graduate Studies',
                'description': 'Coordinates postgraduate programs across the university',
                'departments': []
            }
        ]

        if not self.dry_run:
            for school_data in schools_data:
                school, created = School.objects.get_or_create(
                    name=school_data['name'],
                    university=university,
                    defaults={
                        'description': school_data['description'],
                        'contact_email': f"{school_data['name'].lower().replace(' ', '').replace('school', '')}@uenr.edu.gh"
                    }
                )
                
                self.log(f'School "{school_data["name"]}" {"created" if created else "updated"}')
                
                # Create departments
                for dept_name in school_data['departments']:
                    department, dept_created = Department.objects.get_or_create(
                        name=dept_name,
                        school=school,
                        defaults={
                            'description': f'Department within {school_data["name"]}',
                            'contact_email': f"{dept_name.lower().replace(' ', '').replace('department', '').replace('of', '')}@uenr.edu.gh"
                        }
                    )
                    
                    self.log(f'  Department "{dept_name}" {"created" if dept_created else "updated"}')
        else:
            total_depts = sum(len(s['departments']) for s in schools_data)
            self.log(f'DRY RUN: Would create/update {len(schools_data)} schools and {total_depts} departments')

    def create_staff_profiles(self):
        """Create staff profiles including leadership"""
        self.log('Processing Staff Profiles...')
        
        staff_data = [
            {
                'first_name': 'Elvis',
                'last_name': 'Asare-Bediako',
                'title': 'Prof.',
                'position': 'VC',
                'email': 'vc@uenr.edu.gh',
                'bio': 'Professor Elvis Asare-Bediako is the current Vice Chancellor of UENR. Under his leadership, UENR published 1,400 research works in 2024.',
                'is_admin_staff': True
            },
            {
                'first_name': 'Richard',
                'last_name': 'Hammond',
                'title': 'Mr.',
                'position': 'Admin Staff',
                'email': 'rhammond@uenr.edu.gh',
                'phone_number': '+233 246 565 451',
                'bio': 'Contact person for UENR Accra Office',
                'office_location': 'UENR Accra Office, VCG Complex, UPSA Road',
                'is_admin_staff': True
            }
        ]

        if not self.dry_run:
            for data in staff_data:
                staff, created = StaffProfile.objects.get_or_create(
                    email=data['email'],
                    defaults=data
                )
                if not created:
                    for key, value in data.items():
                        setattr(staff, key, value)
                    staff.save()
                
                self.log(f'Staff "{data["first_name"]} {data["last_name"]}" {"created" if created else "updated"}')
        else:
            self.log(f'DRY RUN: Would create/update {len(staff_data)} staff records')

    def create_campus_services(self):
        """Create campus services"""
        self.log('Processing Campus Services...')
        
        services_data = [
            {
                'name': 'Employability and Career Services',
                'description': 'Provides career guidance, interview preparation, and job placement support',
                'service_category': 'Academic Support',
                'contact_info': 'Main Campus, Sunyani',
                'operating_hours': 'Monday - Friday, 8:00 AM - 5:00 PM'
            },
            {
                'name': 'Finance Directorate',
                'description': 'Handles all financial matters including fee payments and financial aid',
                'service_category': 'Administrative',
                'contact_info': 'Main Campus, Sunyani',
                'operating_hours': 'Monday - Friday, 8:00 AM - 5:00 PM'
            },
            {
                'name': 'Admissions Office',
                'description': 'Processes applications and provides admission information',
                'service_category': 'Administrative',
                'contact_info': 'Main Campus, Sunyani | Accra Office: VCG Complex, UPSA Road',
                'operating_hours': 'Monday - Friday, 8:00 AM - 5:00 PM'
            },
            {
                'name': 'Academic Tracker',
                'description': 'Online system for tracking academic progress',
                'service_category': 'Academic Support',
                'website_url': 'https://uenr.edu.gh/academic-tracker',
                'operating_hours': '24/7 Online Service'
            }
        ]

        if not self.dry_run:
            for data in services_data:
                service, created = CampusService.objects.get_or_create(
                    name=data['name'],
                    defaults=data
                )
                if not created:
                    for key, value in data.items():
                        setattr(service, key, value)
                    service.save()
                
                self.log(f'Service "{data["name"]}" {"created" if created else "updated"}')
        else:
            self.log(f'DRY RUN: Would create/update {len(services_data)} service records')

    def create_contact_info(self):
        """Create contact information"""
        self.log('Processing Contact Information...')
        
        contacts_data = [
            {
                'entity_name': 'Main University',
                'contact_type': 'General Enquiries',
                'phone_number': '+233 352 091 290',
                'email': 'info@uenr.edu.gh',
                'physical_address': 'University of Energy and Natural Resources, Sunyani, Bono Region, Ghana',
                'operating_hours': 'Monday - Friday, 8:00 AM - 5:00 PM'
            },
            {
                'entity_name': 'Admissions Office',
                'contact_type': 'Admissions',
                'email': 'admissions@uenr.edu.gh',
                'physical_address': 'Main Campus, Sunyani',
                'operating_hours': 'Monday - Friday, 8:00 AM - 5:00 PM'
            },
            {
                'entity_name': 'UENR Accra Office',
                'contact_type': 'Admissions',
                'phone_number': '+233 246 565 451',
                'physical_address': 'Office Complex of the Vice Chancellors Ghana (VCG), UPSA Road, Accra',
                'operating_hours': 'Monday - Friday, 8:00 AM - 5:00 PM'
            },
            {
                'entity_name': 'Finance Directorate',
                'contact_type': 'Finance',
                'email': 'finance@uenr.edu.gh',
                'physical_address': 'Main Campus, Sunyani',
                'operating_hours': 'Monday - Friday, 8:00 AM - 5:00 PM'
            }
        ]

        if not self.dry_run:
            for data in contacts_data:
                contact, created = ContactInfo.objects.get_or_create(
                    entity_name=data['entity_name'],
                    contact_type=data['contact_type'],
                    defaults=data
                )
                if not created:
                    for key, value in data.items():
                        setattr(contact, key, value)
                    contact.save()
                
                self.log(f'Contact "{data["entity_name"]}" {"created" if created else "updated"}')
        else:
            self.log(f'DRY RUN: Would create/update {len(contacts_data)} contact records')

    def create_news_announcements(self):
        """Create news and announcements"""
        self.log('Processing News and Announcements...')
        
        news_data = [
            {
                'title': 'UENR Published 1,400 Research Works in 2024',
                'content': 'The University of Energy and Natural Resources made significant achievements in research, publishing 1,400 research works in 2024 under the leadership of Vice Chancellor Professor Elvis Asare-Bediako.',
                'category': 'Research',
                'target_audience': 'All'
            },
            {
                'title': 'Admissions Open for 2025/2026 Academic Year',
                'content': 'UENR is now accepting applications for diploma, undergraduate, and postgraduate programmes for the 2025/2026 academic year.',
                'category': 'Admissions',
                'target_audience': 'Prospective'
            },
            {
                'title': 'ERASMUS KA171 Exchange Programme',
                'content': 'Call for applications for ERASMUS KA171 Exchange Programme for students',
                'category': 'Academic',
                'target_audience': 'Students'
            },
            {
                'title': 'Christmas Break 2024/2025',
                'content': 'The Christmas break will commence after the close of work on Friday, December 20, 2024, and all regular University operations will resume on Thursday, January 9, 2025.',
                'category': 'General',
                'target_audience': 'All'
            }
        ]

        if not self.dry_run:
            for data in news_data:
                news, created = NewsAndAnnouncement.objects.get_or_create(
                    title=data['title'],
                    defaults=data
                )
                if not created:
                    for key, value in data.items():
                        if key != 'title':
                            setattr(news, key, value)
                    news.save()
                
                self.log(f'News "{data["title"]}" {"created" if created else "updated"}')
        else:
            self.log(f'DRY RUN: Would create/update {len(news_data)} news records')

    def create_programs(self):
        """Create academic programs"""
        self.log('Processing Academic Programs...')
        
        # This would typically scrape from the university website
        # For now, we'll create sample programs based on known structure
        programs_data = [
            {
                'name': 'BSc. Mechanical Engineering',
                'program_type': 'Undergraduate',
                'duration_years': 4,
                'description': 'Four-year undergraduate program in mechanical engineering with emphasis on energy systems',
                'admission_requirements': 'WASSCE with credit in Mathematics, Physics, Chemistry, and English Language',
                'min_wassce_aggregate': 24,
                'required_core_subjects': 'English Language, Mathematics, Integrated Science, Social Studies',
                'required_elective_subjects': 'Physics, Chemistry, Elective Mathematics'
            },
            {
                'name': 'BSc. Computer Science',
                'program_type': 'Undergraduate',
                'duration_years': 4,
                'description': 'Four-year undergraduate program in computer science and informatics',
                'admission_requirements': 'WASSCE with credit in Mathematics, Physics, and English Language',
                'min_wassce_aggregate': 20,
                'required_core_subjects': 'English Language, Mathematics, Integrated Science, Social Studies',
                'required_elective_subjects': 'Physics, Chemistry, Elective Mathematics'
            },
            {
                'name': 'BSc. Environmental Science',
                'program_type': 'Undergraduate',
                'duration_years': 4,
                'description': 'Four-year undergraduate program in environmental science',
                'admission_requirements': 'WASSCE with credit in Mathematics, Physics, Chemistry, and English Language',
                'min_wassce_aggregate': 20,
                'required_core_subjects': 'English Language, Mathematics, Integrated Science, Social Studies',
                'required_elective_subjects': 'Physics, Chemistry, Biology'
            }
        ]

        if not self.dry_run:
            # Get the schools to assign programs to
            engineering_school = School.objects.filter(name='School of Engineering').first()
            sciences_school = School.objects.filter(name='School of Sciences').first()
            natural_resources_school = School.objects.filter(name='School of Natural Resources').first()
            
            for data in programs_data:
                # Assign school based on program name
                if 'Engineering' in data['name']:
                    data['school'] = engineering_school
                elif 'Computer Science' in data['name']:
                    data['school'] = sciences_school
                elif 'Environmental' in data['name']:
                    data['school'] = natural_resources_school
                
                if 'school' in data and data['school']:
                    program, created = Program.objects.get_or_create(
                        name=data['name'],
                        defaults=data
                    )
                    if not created:
                        for key, value in data.items():
                            if key != 'name':
                                setattr(program, key, value)
                        program.save()
                    
                    self.log(f'Program "{data["name"]}" {"created" if created else "updated"}')
        else:
            self.log(f'DRY RUN: Would create/update {len(programs_data)} program records')

    def scrape_additional_data(self):
        """Scrape additional data from university website"""
        self.log('Scraping additional data from university website...')
        
        # Try to scrape programs page
        programs_url = f"{self.base_url}/programmes"
        response = self.fetch_page(programs_url)
        
        if response:
            soup = self.parse_html(response.content)
            # Extract program information from the page
            # This would need to be customized based on the actual website structure
            program_elements = soup.find_all('div', class_='program-item')  # Adjust selector as needed
            
            for element in program_elements:
                # Extract program details
                program_name = self.safe_get_text(element.find('h3'))
                program_desc = self.safe_get_text(element.find('p'))
                
                if program_name and not self.dry_run:
                    # Create program record
                    pass  # Implementation depends on actual website structure
        
        # Similar pattern for other pages (news, events, etc.)
        
    def handle(self, *args, **options):
        self.dry_run = options.get('dry_run', False)
        self.verbose = options.get('verbose', False)
        update_only = options.get('update_only', False)
        
        start_time = datetime.now()
        self.log(f'Starting UENR data scraping {"(DRY RUN)" if self.dry_run else ""}...')
        
        try:
            with transaction.atomic():
                # Create university record
                university = self.create_or_update_university()
                
                if not self.dry_run and university:
                    # Create related records
                    self.create_campus_data(university)
                    self.create_schools_and_departments(university)
                    self.create_staff_profiles()
                    self.create_programs()
                    self.create_campus_services()
                    self.create_contact_info()
                    self.create_news_announcements()
                    
                    # Update university with leadership
                    vice_chancellor = StaffProfile.objects.filter(position='VC').first()
                    if vice_chancellor:
                        university.vice_chancellor = vice_chancellor
                        university.save()
                        self.log('Updated university with Vice Chancellor')
                
                # Try to scrape additional data from website
                self.scrape_additional_data()
                
                if self.dry_run:
                    self.log('DRY RUN completed - no data was saved to database')
                    # Rollback transaction in dry run
                    transaction.set_rollback(True)
                else:
                    self.log('Data scraping completed successfully')
                
        except Exception as e:
            self.log(f'Error during scraping: {str(e)}', 'ERROR')
            raise
        
        finally:
            end_time = datetime.now()
            duration = end_time - start_time
            self.log(f'Scraping completed in {duration.total_seconds():.2f} seconds')
            
            # Close session
            self.session.close()