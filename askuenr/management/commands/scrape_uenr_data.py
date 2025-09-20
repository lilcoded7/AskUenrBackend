# askuner_core/management/commands/scrape_uenr_data.py

import json
import os
import asyncio
import aiohttp # For making asynchronous HTTP requests
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from datetime import date
from asgiref.sync import sync_to_async # Import sync_to_async

# Import all your models
from askuenr.models.main import ( # Replace 'askuner_core' with your actual app name
    University, Campus, School, Department, StaffProfile, StudentProfile,
    Program, Course, AcademicRecord, GPA, CampusService, FeeStructure,
    NewsAndAnnouncement, Event, Scholarship, FAQ, ContactInfo
)

# --- Gemini API Configuration ---
# Leave API_KEY empty. It will be automatically provided by the Canvas environment.
API_KEY = "AIzaSyBW4ZIegMueMJ4Aek2KEQ5pD2lHb_DlpRY"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}"

class Command(BaseCommand):
    help = 'Scrapes UENR information using Gemini Flash and populates the database.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--full-scrape',
            action='store_true',
            help='Perform a full scrape of all UENR data types.',
        )
        parser.add_argument(
            '--update-news',
            action='store_true',
            help='Only update news and announcements.',
        )
        parser.add_argument(
            '--update-services',
            action='store_true',
            help='Only update campus services.',
        )
        parser.add_argument(
            '--update-fees',
            action='store_true',
            help='Only update fee structures.',
        )
        parser.add_argument(
            '--update-campuses',
            action='store_true',
            help='Only update campus information.',
        )
        parser.add_argument(
            '--update-events',
            action='store_true',
            help='Only update university events.',
        )
        parser.add_argument(
            '--update-scholarships',
            action='store_true',
            help='Only update scholarship information.',
        )
        parser.add_argument(
            '--update-faqs',
            action='store_true',
            help='Only update FAQs.',
        )
        parser.add_argument(
            '--update-contact-info',
            action='store_true',
            help='Only update general contact information.',
        )


    async def _call_gemini_api(self, prompt_text, schema=None):
        """
        Asynchronously calls the Gemini API with a given prompt and optional schema.
        Returns the parsed JSON response or None on error.
        """
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "temperature": 0.2,  # Lower temperature for more deterministic output
                "maxOutputTokens": 2048, # Limit output tokens to prevent excessive length
                "responseSchema": schema if schema else {"type": "STRING"} # Default to string if no schema
            }
        }

        async with aiohttp.ClientSession() as session:
            try:
                self.stdout.write(self.style.NOTICE(f"Calling Gemini API for: {prompt_text[:50]}..."))
                async with session.post(GEMINI_API_URL, headers=headers, json=payload) as response:
                    response_text = await response.text() # Get raw response text for better error logging
                    
                    try:
                        response.raise_for_status() # Raise an exception for HTTP errors (e.g., 400, 500)
                    except aiohttp.ClientResponseError as e:
                        self.stderr.write(self.style.ERROR(f"HTTP error calling Gemini API: {e.status}, message='{e.message}', url='{e.request_info.url}'"))
                        self.stderr.write(self.style.ERROR(f"Gemini raw error response: {response_text[:500]}...")) # Log part of the response
                        return None

                    result = json.loads(response_text) # Parse JSON after status check
                    
                    if result.get("candidates") and result["candidates"][0].get("content") and \
                       result["candidates"][0]["content"].get("parts") and \
                       result["candidates"][0]["content"]["parts"][0].get("text"):
                        
                        json_text = result["candidates"][0]["content"]["parts"][0]["text"]
                        try:
                            parsed_json = json.loads(json_text)
                            self.stdout.write(self.style.SUCCESS("Successfully received and parsed JSON from Gemini."))
                            return parsed_json
                        except json.JSONDecodeError:
                            self.stderr.write(self.style.ERROR(f"Failed to decode JSON from Gemini. Raw text: {json_text[:500]}...")) # Log part of the bad JSON
                            return None
                    else:
                        self.stderr.write(self.style.ERROR(f"Unexpected Gemini response structure: {result}"))
                        return None
            except aiohttp.ClientError as e:
                self.stderr.write(self.style.ERROR(f"HTTP client error calling Gemini API: {e}"))
                return None
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An unexpected error occurred during API call: {e}"))
                return None

    async def _get_uenr_info(self):
        """
        Prompts Gemini to get general UENR information.
        """
        prompt = """
        Provide key information about the University of Energy and Natural Resources (UENR) in Ghana.
        Include its full name, motto, a brief history (max 100 words), vision (max 50 words), mission (max 50 words), core values (max 100 words),
        establishment date (YYYY-MM-DD), contact email, contact phone, and address. Also include its
        accreditation status (max 50 words), national ranking (integer), international ranking (max 50 words), and the current Vice-Chancellor's full name.
        Format the output as a JSON object with keys: "name", "motto", "history", "vision", "mission",
        "core_values", "established_date", "contact_email", "contact_phone", "address",
        "accreditation_status", "national_ranking", "international_ranking", "vice_chancellor_name".
        Ensure the history is concise and factual.
        """
        schema = {
            "type": "OBJECT",
            "properties": {
                "name": {"type": "STRING"},
                "motto": {"type": "STRING"},
                "history": {"type": "STRING"},
                "vision": {"type": "STRING"},
                "mission": {"type": "STRING"},
                "core_values": {"type": "STRING"},
                "established_date": {"type": "STRING", "format": "date"},
                "contact_email": {"type": "STRING", "format": "email"},
                "contact_phone": {"type": "STRING"},
                "address": {"type": "STRING"},
                "accreditation_status": {"type": "STRING"},
                "national_ranking": {"type": "INTEGER"},
                "international_ranking": {"type": "STRING"},
                "vice_chancellor_name": {"type": "STRING"}
            },
            "required": ["name", "history", "vision", "mission"]
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_campuses(self):
        """
        Prompts Gemini to get information about UENR's campuses.
        """
        prompt = """
        List all physical campus locations of the University of Energy and Natural Resources (UENR).
        For each campus, include: "name", "location_address", "description" (max 50 words), and optionally "latitude" and "longitude".
        Format the output as a JSON array of campus objects.
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "location_address": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "latitude": {"type": "NUMBER"},
                    "longitude": {"type": "NUMBER"}
                },
                "required": ["name", "location_address"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_schools_and_departments(self):
        """
        Prompts Gemini to get UENR's schools and their departments.
        """
        prompt = """
        List all academic schools at the University of Energy and Natural Resources (UENR) and for each school,
        list its academic departments.
        Provide a very brief description for each school and department (max 30 words each). Include contact emails and phone numbers if available.
        For schools, also specify which campus they are located on (e.g., Sunyani Campus, Nsoatre Campus, Dormaa Campus).
        Format the output as a JSON array of school objects. Each school object should have:
        "name" (string), "description" (string, optional), "contact_email" (string, optional),
        "contact_phone" (string, optional), "campus_name" (string), and a "departments" array.
        Each department object within "departments" array should have:
        "name" (string), "description" (string, optional), "contact_email" (string, optional),
        "contact_phone" (string, optional), "office_location" (string, optional).
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "contact_email": {"type": "STRING", "format": "email"},
                    "contact_phone": {"type": "STRING"},
                    "campus_name": {"type": "STRING"},
                    "departments": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "name": {"type": "STRING"},
                                "description": {"type": "STRING"},
                                "contact_email": {"type": "STRING"},
                                "contact_phone": {"type": "STRING"},
                                "office_location": {"type": "STRING"}
                            },
                            "required": ["name"]
                        }
                    }
                },
                "required": ["name", "departments", "campus_name"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_programs_and_courses(self):
        """
        Prompts Gemini to get UENR's academic programs and their associated courses.
        """
        prompt = """
        List key academic programs offered by UENR, including their program type (Diploma, Undergraduate, Postgraduate, PhD),
        duration in years, and a brief description (max 80 words). For each program, list its admission requirements (max 100 words, including WASSCE aggregates,
        required core subjects, and required elective subjects), career prospects (max 80 words), and program accreditation status (max 50 words).
        Also, list 3-5 of its core courses with their codes, titles, credit hours, descriptions (max 50 words), prerequisites (course codes),
        learning outcomes (max 50 words), and a URL for course materials if available.
        Focus on the most prominent programs.
        Format the output as a JSON array of program objects. Each program object should have:
        "name" (string), "program_type" (string, e.g., "Undergraduate"), "duration_years" (integer),
        "description" (string, optional), "admission_requirements" (string, optional),
        "min_wassce_aggregate" (integer, optional), "required_core_subjects" (string, comma-separated, optional),
        "required_elective_subjects" (string, comma-separated, optional),
        "career_prospects" (string, optional), "accreditation_status" (string, optional),
        "program_coordinator_email" (string, optional), and a "courses" array.
        Each course object within "courses" array should have:
        "code" (string), "title" (string), "credit_hours" (number), "description" (string, optional),
        "prerequisites": {"type": "ARRAY", "items": {"type": "STRING"}},
        "learning_outcomes": {"type": "STRING"},
        "course_materials_url": {"type": "STRING", "format": "uri"}
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "program_type": {"type": "STRING"},
                    "duration_years": {"type": "INTEGER"},
                    "description": {"type": "STRING"},
                    "admission_requirements": {"type": "STRING"},
                    "min_wassce_aggregate": {"type": "INTEGER"},
                    "required_core_subjects": {"type": "STRING"},
                    "required_elective_subjects": {"type": "STRING"},
                    "career_prospects": {"type": "STRING"},
                    "accreditation_status": {"type": "STRING"},
                    "program_coordinator_email": {"type": "STRING", "format": "email"},
                    "courses": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "code": {"type": "STRING"},
                                "title": {"type": "STRING"},
                                "credit_hours": {"type": "NUMBER"},
                                "description": {"type": "STRING"},
                                "prerequisites": {"type": "ARRAY", "items": {"type": "STRING"}},
                                "learning_outcomes": {"type": "STRING"},
                                "course_materials_url": {"type": "STRING", "format": "uri"}
                            },
                            "required": ["code", "title", "credit_hours"]
                        }
                    }
                },
                "required": ["name", "program_type", "duration_years"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_staff_profiles(self):
        """
        Prompts Gemini to get profiles of key staff (e.g., VC, Pro-VC, Registrar, Deans, HoDs).
        """
        prompt = """
        Provide profiles for 5-10 key administrative staff, deans of schools, and heads of departments at UENR.
        For each person, include: "first_name", "last_name", "title" (e.g., "Prof.", "Dr."),
        "position" (e.g., "Vice-Chancellor", "Dean", "Head of Department", "Senior Lecturer"),
        "email", "phone_number" (optional), "bio" (max 50 words), "research_interests" (max 50 words),
        "academic_qualifications" (max 100 words), "office_location" (max 50 words), "office_hours" (max 50 words), "google_scholar_url",
        "researchgate_url", "linkedin_url".
        Indicate if they are a "Head of Department" (is_hod: true/false), "Dean" (is_dean: true/false),
        or "Administrative Staff" (is_admin_staff: true/false).
        Format as a JSON array of staff objects.
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "first_name": {"type": "STRING"},
                    "last_name": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "position": {"type": "STRING"},
                    "email": {"type": "STRING", "format": "email"},
                    "phone_number": {"type": "STRING"},
                    "bio": {"type": "STRING"},
                    "research_interests": {"type": "STRING"},
                    "academic_qualifications": {"type": "STRING"},
                    "office_location": {"type": "STRING"},
                    "office_hours": {"type": "STRING"},
                    "google_scholar_url": {"type": "STRING", "format": "uri"},
                    "researchgate_url": {"type": "STRING", "format": "uri"},
                    "linkedin_url": {"type": "STRING", "format": "uri"},
                    "is_hod": {"type": "BOOLEAN"},
                    "is_dean": {"type": "BOOLEAN"},
                    "is_admin_staff": {"type": "BOOLEAN"}
                },
                "required": ["first_name", "last_name", "position", "email"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_news_and_announcements(self):
        """
        Prompts Gemini to get recent news and announcements from UENR.
        """
        prompt = """
        List 5-10 recent important news and announcements from the University of Energy and Natural Resources (UENR).
        For each item, include: "title", "content" (brief summary, max 150 words), "publish_date" (YYYY-MM-DD),
        "target_audience" (e.g., "All", "Students", "Staff", "Prospective"),
        "category" (e.g., "Admissions", "Events", "Policy", "General", "Research"),
        "event_date_time" (YYYY-MM-DDTHH:MM:SS, if applicable), and "external_link".
        Format as a JSON array of news objects.
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "content": {"type": "STRING"},
                    "publish_date": {"type": "STRING", "format": "date"},
                    "target_audience": {"type": "STRING"},
                    "category": {"type": "STRING"},
                    "event_date_time": {"type": "STRING", "format": "date-time"},
                    "external_link": {"type": "STRING", "format": "uri"}
                },
                "required": ["title", "content", "publish_date"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_campus_services(self):
        """
        Prompts Gemini to get information about campus services at UENR.
        """
        prompt = """
        List 5-7 key campus services available at the University of Energy and Natural Resources (UENR).
        For each service, include: "name", "description" (max 80 words), "contact_info" (phone, email, office hours),
        "location" (on campus), "operating_hours", "website_url", "service_category" (e.g., "Academic Support", "Student Life", "IT Support").
        Focus on common services.
        Format as a JSON array of service objects.
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "contact_info": {"type": "STRING"},
                    "location": {"type": "STRING"},
                    "operating_hours": {"type": "STRING"},
                    "website_url": {"type": "STRING", "format": "uri"},
                    "service_category": {"type": "STRING"}
                },
                "required": ["name", "description"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_fees_structure(self):
        """
        Prompts Gemini to get information about UENR's fee structure.
        """
        prompt = """
        Provide general information about the fee structure for academic programs at the University of Energy and Natural Resources (UENR) for the current or most recent academic year.
        Include typical "fee_type" (e.g., "Tuition", "Accommodation", "Examination", "Other", "Application", "Graduation"),
        approximate "amount" (number), the "academic_year" (YYYY/YYYY), "program_name" (optional),
        "notes" (payment deadlines, installment options, max 80 words), "currency" (e.g., GHS, USD), and "payment_methods" (e.g., Bank Transfer, Mobile Money).
        Also, indicate if the fee is "is_refundable" (true/false).
        Focus on a few examples if specific details are hard to find.
        Format as a JSON array of fee objects.
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "fee_type": {"type": "STRING"},
                    "amount": {"type": "NUMBER"},
                    "academic_year": {"type": "STRING"},
                    "program_name": {"type": "STRING"},
                    "notes": {"type": "STRING"},
                    "currency": {"type": "STRING"},
                    "payment_methods": {"type": "STRING"},
                    "is_refundable": {"type": "BOOLEAN"}
                },
                "required": ["fee_type", "amount", "academic_year"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_events(self):
        """
        Prompts Gemini to get information about upcoming or recent events at UENR.
        """
        prompt = """
        List 5-10 upcoming or recent events at the University of Energy and Natural Resources (UENR).
        For each event, include: "name", "description" (max 150 words), "start_date_time" (YYYY-MM-DDTHH:MM:SS),
        "end_date_time" (optional, YYYY-MM-DDTHH:MM:SS), "location", "event_type" (e.g., "Academic", "Social", "Sports"),
        "organizer", "contact_email", "contact_phone", "registration_link", and "is_public" (true/false).
        Format as a JSON array of event objects.
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "start_date_time": {"type": "STRING", "format": "date-time"},
                    "end_date_time": {"type": "STRING", "format": "date-time"},
                    "location": {"type": "STRING"},
                    "event_type": {"type": "STRING"},
                    "organizer": {"type": "STRING"},
                    "contact_email": {"type": "STRING", "format": "email"},
                    "contact_phone": {"type": "STRING"},
                    "registration_link": {"type": "STRING", "format": "uri"},
                    "is_public": {"type": "BOOLEAN"}
                },
                "required": ["name", "description", "start_date_time", "location"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_scholarships(self):
        """
        Prompts Gemini to get information about available scholarships at UENR.
        """
        prompt = """
        List 5-10 available scholarships for students at the University of Energy and Natural Resources (UENR).
        For each scholarship, include: "name", "description" (max 150 words), "scholarship_type" (e.g., "Merit-based", "Need-based"),
        "eligibility_criteria" (max 150 words), "application_deadline" (YYYY-MM-DD), "amount_or_benefits" (max 80 words),
        "application_link", "contact_info" (max 80 words), and "is_active" (true/false).
        Format as a JSON array of scholarship objects.
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "name": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "scholarship_type": {"type": "STRING"},
                    "eligibility_criteria": {"type": "STRING"},
                    "application_deadline": {"type": "STRING", "format": "date"},
                    "amount_or_benefits": {"type": "STRING"},
                    "application_link": {"type": "STRING", "format": "uri"},
                    "contact_info": {"type": "STRING"},
                    "is_active": {"type": "BOOLEAN"}
                },
                "required": ["name", "description", "scholarship_type", "eligibility_criteria"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_faqs(self):
        """
        Prompts Gemini to get common FAQs and answers related to UENR.
        """
        prompt = """
        List 10-15 common Frequently Asked Questions (FAQs) and their answers related to the University of Energy and Natural Resources (UENR).
        For each FAQ, include: "question", "answer" (max 200 words), and "category" (e.g., "Admissions", "Academics", "Fees & Financial Aid", "Campus Life").
        Format as a JSON array of FAQ objects.
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "question": {"type": "STRING"},
                    "answer": {"type": "STRING"},
                    "category": {"type": "STRING"}
                },
                "required": ["question", "answer"]
            }
        }
        return await self._call_gemini_api(prompt, schema)

    async def _get_contact_info(self):
        """
        Prompts Gemini to get general contact information for various UENR offices.
        """
        prompt = """
        List key contact information for various offices and entities at the University of Energy and Natural Resources (UENR).
        For each contact, include: "entity_name" (e.g., "Admissions Office", "Registrar's Office"),
        "contact_type" (e.g., "Admissions", "Registrar", "IT Helpdesk"), "phone_number", "email",
        "physical_address" (max 100 words), "operating_hours" (max 50 words), and "website_url" (optional).
        Format as a JSON array of contact objects.
        """
        schema = {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "entity_name": {"type": "STRING"},
                    "contact_type": {"type": "STRING"},
                    "phone_number": {"type": "STRING"},
                    "email": {"type": "STRING", "format": "email"},
                    "physical_address": {"type": "STRING"},
                    "operating_hours": {"type": "STRING"},
                    "website_url": {"type": "STRING", "format": "uri"}
                },
                "required": ["entity_name", "contact_type"]
            }
        }
        return await self._call_gemini_api(prompt, schema)


    async def handle_async(self, *args, **options):
        """
        Main asynchronous handler for the Django command.
        """
        self.stdout.write(self.style.SUCCESS("Starting UENR data scraping..."))

        # Get the single University instance or create it
        university, created = await sync_to_async(University.objects.get_or_create)(
            name="University of Energy and Natural Resources",
            defaults={
                'history': "Initial history placeholder.",
                'vision': "Initial vision placeholder.",
                'mission': "Initial mission placeholder.",
                'established_date': date(2011, 12, 31)
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS("Created initial University instance."))
        else:
            self.stdout.write(self.style.SUCCESS("Found existing University instance."))

        # Determine if any specific update flag is set
        any_update_flag_set = (
            options['update_news'] or options['update_services'] or
            options['update_fees'] or options['update_campuses'] or
            options['update_events'] or options['update_scholarships'] or
            options['update_faqs'] or options['update_contact_info']
        )

        # Default to full scrape if no specific update flag is given
        if options['full_scrape'] or not any_update_flag_set:
            await self._perform_full_scrape(university)
        elif options['update_news']:
            await self._update_news_and_announcements()
        elif options['update_services']:
            await self._update_campus_services()
        elif options['update_fees']:
            await self._update_fees_structure()
        elif options['update_campuses']:
            await self._update_campuses(university)
        elif options['update_events']:
            await self._update_events()
        elif options['update_scholarships']:
            await self._update_scholarships()
        elif options['update_faqs']:
            await self._update_faqs()
        elif options['update_contact_info']:
            await self._update_contact_info()

        self.stdout.write(self.style.SUCCESS("UENR data scraping complete."))

    async def _perform_full_scrape(self, university):
        """Performs a comprehensive scrape and populates all related models."""
        self.stdout.write(self.style.MIGRATE_HEADING("Performing full scrape..."))

        # 1. Scrape and update University info
        self.stdout.write(self.style.NOTICE("Scraping general UENR information..."))
        uenr_info = await self._get_uenr_info()
        if uenr_info:
            try:
                # Update the existing university instance
                university.motto = uenr_info.get('motto', '')
                university.history = uenr_info.get('history', university.history)
                university.vision = uenr_info.get('vision', university.vision)
                university.mission = uenr_info.get('mission', university.mission)
                university.core_values = uenr_info.get('core_values', '')
                if uenr_info.get('established_date'):
                    try:
                        university.established_date = date.fromisoformat(uenr_info['established_date'])
                    except ValueError:
                        self.stderr.write(self.style.WARNING(f"Invalid date format for established_date: {uenr_info['established_date']}"))
                university.contact_email = uenr_info.get('contact_email', '')
                university.contact_phone = uenr_info.get('contact_phone', '')
                university.address = uenr_info.get('address', '')
                university.accreditation_status = uenr_info.get('accreditation_status', '')
                university.national_ranking = uenr_info.get('national_ranking', None)
                university.international_ranking = uenr_info.get('international_ranking', '')
                
                # Link Vice-Chancellor if staff profile exists
                vc_name = uenr_info.get('vice_chancellor_name')
                if vc_name:
                    # Heuristic: try to find by last name, then first name
                    vc_profile = await sync_to_async(StaffProfile.objects.filter(
                        last_name__icontains=vc_name.split()[-1]
                    ).first)()
                    if vc_profile:
                        university.vice_chancellor = vc_profile
                    else:
                        self.stderr.write(self.style.WARNING(f"Vice-Chancellor profile not found for: {vc_name}"))

                await sync_to_async(university.save)() # Wrap save with sync_to_async
                self.stdout.write(self.style.SUCCESS("University information updated successfully."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Error updating University info: {e}"))

        # 2. Scrape and save Campuses
        await self._update_campuses(university)

        # 3. Scrape and save Schools and Departments
        self.stdout.write(self.style.NOTICE("Scraping Schools and Departments..."))
        schools_data = await self._get_schools_and_departments()
        if schools_data:
            @sync_to_async
            @transaction.atomic
            def _save_schools_and_departments():
                for school_data in schools_data:
                    # Link to Campus
                    related_campus = None
                    if school_data.get('campus_name'):
                        related_campus = Campus.objects.filter(name__icontains=school_data['campus_name']).first()

                    school, created = School.objects.update_or_create(
                        name=school_data['name'],
                        university=university,
                        defaults={
                            'description': school_data.get('description', ''),
                            'contact_email': school_data.get('contact_email', ''),
                            'contact_phone': school_data.get('contact_phone', ''),
                            'campus': related_campus # Assign campus
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"School '{school.name}' {'created' if created else 'updated'}."))

                    for dept_data in school_data.get('departments', []):
                        department, created = Department.objects.update_or_create(
                            name=dept_data['name'],
                            school=school,
                            defaults={
                                'description': dept_data.get('description', ''),
                                'contact_email': dept_data.get('contact_email', ''),
                                'contact_phone': dept_data.get('contact_phone', ''),
                                'office_location': dept_data.get('office_location', '')
                            }
                        )
                        self.stdout.write(self.style.SUCCESS(f"  Department '{department.name}' {'created' if created else 'updated'}."))
            await _save_schools_and_departments() # Call the wrapped function
        else:
            self.stderr.write(self.style.WARNING("No Schools and Departments data received from Gemini."))

        # 4. Scrape and save Programs and Courses
        self.stdout.write(self.style.NOTICE("Scraping Programs and Courses..."))
        programs_data = await self._get_programs_and_courses()
        if programs_data:
            @sync_to_async
            @transaction.atomic
            def _save_programs_and_courses():
                for program_data in programs_data:
                    # Try to link program to an existing school/department
                    related_school = School.objects.filter(name__icontains=program_data.get('school_name', '')).first()
                    related_department = Department.objects.filter(name__icontains=program_data.get('department_name', '')).first()
                    
                    program_coordinator = None
                    if program_data.get('program_coordinator_email'):
                        program_coordinator = StaffProfile.objects.filter(email=program_data['program_coordinator_email']).first()

                    program, created = Program.objects.update_or_create(
                        name=program_data['name'],
                        program_type=program_data['program_type'],
                        defaults={
                            'school': related_school, # Can be None if not found
                            'department': related_department, # Can be None if not found
                            'duration_years': program_data.get('duration_years', 4),
                            'description': program_data.get('description', ''),
                            'admission_requirements': program_data.get('admission_requirements', ''),
                            'min_wassce_aggregate': program_data.get('min_wassce_aggregate', None),
                            'required_core_subjects': program_data.get('required_core_subjects', ''),
                            'required_elective_subjects': program_data.get('required_elective_subjects', ''),
                            'career_prospects': program_data.get('career_prospects', ''),
                            'accreditation_status': program_data.get('accreditation_status', ''),
                            'program_coordinator': program_coordinator,
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"Program '{program.name}' {'created' if created else 'updated'}."))

                    for course_data in program_data.get('courses', []):
                        # Try to link course to its department
                        course_department = Department.objects.filter(name__icontains=course_data.get('department_name', '')).first()
                        if not course_department and related_department: # Fallback to program's department
                            course_department = related_department

                        course, created = Course.objects.update_or_create(
                            code=course_data['code'],
                            defaults={
                                'title': course_data['title'],
                                'credit_hours': course_data['credit_hours'],
                                'description': course_data.get('description', ''),
                                'department': course_department, # Can be None
                                'learning_outcomes': course_data.get('learning_outcomes', ''),
                                'course_materials_url': course_data.get('course_materials_url', ''),
                                # semester_offered and lecturers will be set later or manually
                            }
                        )
                        course.programs.add(program) # Link course to program
                        
                        # Add prerequisites
                        if course_data.get('prerequisites'):
                            prereq_codes = course_data['prerequisites']
                            prereq_courses = Course.objects.filter(code__in=prereq_codes)
                            course.prerequisites.set(prereq_courses) # Use .set() to replace existing
                        
                        self.stdout.write(self.style.SUCCESS(f"  Course '{course.code}' {'created' if created else 'updated'} and linked to program."))
            await _save_programs_and_courses() # Call the wrapped function
        else:
            self.stderr.write(self.style.WARNING("No Programs and Courses data received from Gemini."))

        # 5. Scrape and save Staff Profiles
        self.stdout.write(self.style.NOTICE("Scraping Staff Profiles..."))
        staff_data = await self._get_staff_profiles()
        if staff_data:
            @sync_to_async
            @transaction.atomic
            def _save_staff_profiles():
                for person_data in staff_data:
                    # Attempt to link staff to an existing department based on their position/bio
                    linked_department = None
                    if "Head of Department" in person_data.get('position', '') or person_data.get('is_hod'):
                        for dept_name in Department.objects.values_list('name', flat=True):
                            if dept_name.lower() in person_data.get('bio', '').lower() or \
                               f"head of {dept_name.lower()}" in person_data.get('position', '').lower():
                                linked_department = Department.objects.get(name=dept_name)
                                break
                    elif "Dean" in person_data.get('position', '') or person_data.get('is_dean'):
                         pass # Dean-School linking handled below

                    staff_profile, created = StaffProfile.objects.update_or_create(
                        email=person_data['email'],
                        defaults={
                            'first_name': person_data['first_name'],
                            'last_name': person_data['last_name'],
                            'title': person_data.get('title', ''),
                            'position': person_data['position'],
                            'phone_number': person_data.get('phone_number', ''),
                            'bio': person_data.get('bio', ''),
                            'research_interests': person_data.get('research_interests', ''),
                            'is_hod': person_data.get('is_hod', False),
                            'is_dean': person_data.get('is_dean', False),
                            'is_admin_staff': person_data.get('is_admin_staff', False),
                            'department': linked_department,
                            'academic_qualifications': person_data.get('academic_qualifications', ''),
                            'office_location': person_data.get('office_location', ''),
                            'office_hours': person_data.get('office_hours', ''),
                            'google_scholar_url': person_data.get('google_scholar_url', ''),
                            'researchgate_url': person_data.get('researchgate_url', ''),
                            'linkedin_url': person_data.get('linkedin_url', ''),
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"Staff '{staff_profile.first_name} {staff_profile.last_name}' {'created' if created else 'updated'}."))

                    # Special handling for Dean/HOD assignments in School/Department models
                    if staff_profile.is_dean:
                        school_name_in_bio = next((s.name for s in School.objects.all() if s.name.lower() in staff_profile.bio.lower()), None)
                        if school_name_in_bio:
                            school_obj = School.objects.filter(name=school_name_in_bio).first()
                            if school_obj:
                                school_obj.dean = staff_profile
                                school_obj.save()
                                self.stdout.write(self.style.SUCCESS(f"  Assigned {staff_profile.first_name} as Dean of {school_obj.name}."))
                    if staff_profile.is_hod and linked_department:
                        linked_department.head_of_department = staff_profile
                        linked_department.save()
                        self.stdout.write(self.style.SUCCESS(f"  Assigned {staff_profile.first_name} as HOD of {linked_department.name}."))
            await _save_staff_profiles() # Call the wrapped function
        else:
            self.stderr.write(self.style.WARNING("No Staff Profiles data received from Gemini."))

        # 6. Scrape and update News and Announcements
        await self._update_news_and_announcements()

        # 7. Scrape and update Campus Services
        await self._update_campus_services()

        # 8. Scrape and update Fee Structures
        await self._update_fees_structure()

        # 9. Scrape and update Events
        await self._update_events()

        # 10. Scrape and update Scholarships
        await self._update_scholarships()

        # 11. Scrape and update FAQs
        await self._update_faqs()

        # 12. Scrape and update Contact Info
        await self._update_contact_info()


    async def _update_campuses(self, university):
        """Scrapes and updates campus information."""
        self.stdout.write(self.style.NOTICE("Scraping Campus Information..."))
        campuses_data = await self._get_campuses()
        if campuses_data:
            @sync_to_async
            @transaction.atomic
            def _save_campuses():
                for campus_item in campuses_data:
                    campus, created = Campus.objects.update_or_create(
                        name=campus_item['name'],
                        university=university,
                        defaults={
                            'location_address': campus_item.get('location_address', ''),
                            'description': campus_item.get('description', ''),
                            'latitude': campus_item.get('latitude', None),
                            'longitude': campus_item.get('longitude', None),
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"Campus '{campus.name}' {'created' if created else 'updated'}."))
            await _save_campuses()
        else:
            self.stderr.write(self.style.WARNING("No Campus data received from Gemini."))

    async def _update_events(self):
        """Scrapes and updates university events."""
        self.stdout.write(self.style.NOTICE("Scraping Events..."))
        events_data = await self._get_events()
        if events_data:
            @sync_to_async
            @transaction.atomic
            def _save_events():
                for event_item in events_data:
                    try:
                        start_dt = timezone.datetime.fromisoformat(event_item['start_date_time'])
                        end_dt = timezone.datetime.fromisoformat(event_item['end_date_time']) if event_item.get('end_date_time') else None
                    except ValueError:
                        self.stderr.write(self.style.WARNING(f"Invalid date/time format for event '{event_item.get('name', 'Unknown')}'. Skipping."))
                        continue

                    event, created = Event.objects.update_or_create(
                        name=event_item['name'],
                        start_date_time=start_dt, # Use start_date_time as part of unique identifier
                        defaults={
                            'description': event_item['description'],
                            'end_date_time': end_dt,
                            'location': event_item['location'],
                            'event_type': event_item.get('event_type', 'Other'),
                            'organizer': event_item.get('organizer', ''),
                            'contact_email': event_item.get('contact_email', ''),
                            'contact_phone': event_item.get('contact_phone', ''),
                            'registration_link': event_item.get('registration_link', ''),
                            'is_public': event_item.get('is_public', True),
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"Event '{event.name}' {'created' if created else 'updated'}."))
            await _save_events()
        else:
            self.stderr.write(self.style.WARNING("No Event data received from Gemini."))

    async def _update_scholarships(self):
        """Scrapes and updates scholarship information."""
        self.stdout.write(self.style.NOTICE("Scraping Scholarships..."))
        scholarships_data = await self._get_scholarships()
        if scholarships_data:
            @sync_to_async
            @transaction.atomic
            def _save_scholarships():
                for scholarship_item in scholarships_data:
                    try:
                        deadline = date.fromisoformat(scholarship_item['application_deadline']) if scholarship_item.get('application_deadline') else None
                    except ValueError:
                        self.stderr.write(self.style.WARNING(f"Invalid date format for scholarship deadline '{scholarship_item.get('name', 'Unknown')}'. Skipping."))
                        continue

                    scholarship, created = Scholarship.objects.update_or_create(
                        name=scholarship_item['name'],
                        defaults={
                            'description': scholarship_item['description'],
                            'scholarship_type': scholarship_item['scholarship_type'],
                            'eligibility_criteria': scholarship_item['eligibility_criteria'],
                            'application_deadline': deadline,
                            'amount_or_benefits': scholarship_item.get('amount_or_benefits', ''),
                            'application_link': scholarship_item.get('application_link', ''),
                            'contact_info': scholarship_item.get('contact_info', ''),
                            'is_active': scholarship_item.get('is_active', True),
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"Scholarship '{scholarship.name}' {'created' if created else 'updated'}."))
            await _save_scholarships()
        else:
            self.stderr.write(self.style.WARNING("No Scholarship data received from Gemini."))

    async def _update_faqs(self):
        """Scrapes and updates FAQs."""
        self.stdout.write(self.style.NOTICE("Scraping FAQs..."))
        faqs_data = await self._get_faqs()
        if faqs_data:
            @sync_to_async
            @transaction.atomic
            def _save_faqs():
                for faq_item in faqs_data:
                    faq, created = FAQ.objects.update_or_create(
                        question=faq_item['question'],
                        defaults={
                            'answer': faq_item['answer'],
                            'category': faq_item.get('category', 'General'),
                            # related_programs and related_departments would need more sophisticated linking
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"FAQ '{faq.question[:50]}...' {'created' if created else 'updated'}."))
            await _save_faqs()
        else:
            self.stderr.write(self.style.WARNING("No FAQ data received from Gemini."))

    async def _update_contact_info(self):
        """Scrapes and updates general contact information."""
        self.stdout.write(self.style.NOTICE("Scraping Contact Information..."))
        contact_info_data = await self._get_contact_info()
        if contact_info_data:
            @sync_to_async
            @transaction.atomic
            def _save_contact_info():
                for contact_item in contact_info_data:
                    contact, created = ContactInfo.objects.update_or_create(
                        entity_name=contact_item['entity_name'],
                        contact_type=contact_item['contact_type'],
                        defaults={
                            'phone_number': contact_item.get('phone_number', ''),
                            'email': contact_item.get('email', ''),
                            'physical_address': contact_item.get('physical_address', ''),
                            'operating_hours': contact_item.get('operating_hours', ''),
                            'website_url': contact_item.get('website_url', ''),
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"Contact Info for '{contact.entity_name}' {'created' if created else 'updated'}."))
            await _save_contact_info()
        else:
            self.stderr.write(self.style.WARNING("No Contact Information data received from Gemini."))

    async def _update_news_and_announcements(self):
        """Scrapes and updates news and announcements."""
        self.stdout.write(self.style.NOTICE("Scraping News and Announcements..."))
        news_data = await self._get_news_and_announcements()
        if news_data:
            # Find a default author, e.g., the first admin staff, or create a placeholder
            default_author = await sync_to_async(StaffProfile.objects.filter(is_admin_staff=True).first)()
            if not default_author:
                default_author, _ = await sync_to_async(StaffProfile.objects.get_or_create)(
                    email="admin@uenr.edu.gh",
                    defaults={'first_name': 'UENR', 'last_name': 'Admin', 'position': 'Administrative Staff', 'is_admin_staff': True}
                )

            @sync_to_async
            @transaction.atomic
            def _save_news_and_announcements():
                for news_item in news_data:
                    # Ensure publish_date is a date object
                    try:
                        # Handle both date and datetime formats
                        if 'T' in news_item['publish_date']:
                            publish_date = timezone.datetime.fromisoformat(news_item['publish_date'])
                        else:
                            publish_date = timezone.datetime.combine(date.fromisoformat(news_item['publish_date']), timezone.datetime.min.time())

                        event_date_time = None
                        if news_item.get('event_date_time'):
                            event_date_time = timezone.datetime.fromisoformat(news_item['event_date_time'])

                    except ValueError as e:
                        self.stderr.write(self.style.WARNING(f"Invalid date/time format for news item '{news_item.get('title', 'Unknown')}' ({e}). Skipping news item."))
                        continue

                    # Use title and publish_date as a unique identifier for news updates
                    news, created = NewsAndAnnouncement.objects.update_or_create(
                        title=news_item['title'],
                        publish_date=publish_date,
                        defaults={
                            'content': news_item['content'],
                            'target_audience': news_item.get('target_audience', 'All'),
                            'category': news_item.get('category', 'General'),
                            'author': default_author,
                            'event_date_time': event_date_time,
                            'external_link': news_item.get('external_link', ''),
                        }
                    )
                    self.stdout.write(self.style.SUCCESS(f"News '{news.title}' {'created' if created else 'updated'}."))
            await _save_news_and_announcements() # Call the wrapped function
        else:
            self.stderr.write(self.style.WARNING("No News and Announcements data received from Gemini."))

    def handle(self, *args, **options):
        """
        Entry point for the Django command. Runs the async handler.
        """
        # Run the asynchronous function
        asyncio.run(self.handle_async(*args, **options))

