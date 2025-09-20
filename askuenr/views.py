# askuenr/views.py

from pathlib import Path
import json
import asyncio
import aiohttp
import uuid
import re
from collections import Counter

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from askuenr.models.chat import ChatConversation
from askuenr.serializers import MessageSerializer
from django.conf import settings

# --- Gemini API Config ---
API_KEY = "AIzaSyBW4ZIegMueMJ4Aek2KEQ5pD2lHb_DlpRY"
GEMINI_API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.API_KEY}"

# --- JSON Data Paths ---
DATA_DIR = Path(__file__).resolve().parent / "data"
STAFF_JSON_PATH = DATA_DIR / "staffs.json"
GUIDE_JSON_PATH = DATA_DIR / "uenr_academic_and_student_guide.json"
IT_DEPT_JSON_PATH = DATA_DIR / "it_department_info.json"


class AskUnerAPIView(APIView):
    """
    Handles Q&A for UENR using JSON knowledge base + Gemini AI fallback.
    """
    MIN_RESPONSE_LENGTH = 50
    MAX_RESPONSE_LENGTH = 1500

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize data attributes
        self.staff_data = None
        self.guide_data = None
        self.it_dept_data = None
        
    # ---------------- JSON HELPERS ----------------
    def _load_json(self, path: Path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading {path}: {e}")
            return None

    def _initialize_data(self):
        """Initialize data on first use"""
        if self.staff_data is None:
            self.staff_data = self._load_json(STAFF_JSON_PATH) or []
        if self.guide_data is None:
            self.guide_data = self._load_json(GUIDE_JSON_PATH) or {}
        if self.it_dept_data is None:
            self.it_dept_data = self._load_json(IT_DEPT_JSON_PATH) or {}

    # ---------------- ADVANCED QUESTION UNDERSTANDING ----------------
    def _understand_question(self, question: str):
        """
        Analyze the question to understand what information is being requested.
        """
        q_lower = question.lower()
        analysis = {
            "type": "general",
            "target_person": None,
            "target_department": None,
            "target_program": None,
            "target_topic": None,
            "keywords": [],
            "is_uenr_related": True
        }
        
        # Extract keywords
        words = re.findall(r'\b[a-z]{3,}\b', q_lower)  # Only words with 3+ characters
        analysis["keywords"] = words
        
        # Check for person queries
        person_keywords = ["who", "prof", "dr", "mr", "mrs", "ms", "director", "dean", "head", "vc", "vice-chancellor"]
        if any(word in q_lower for word in person_keywords):
            analysis["type"] = "person_query"
            
            # Try to extract person name
            name_patterns = [
                r"(prof\.?|dr\.?|mr\.?|mrs\.?|ms\.?)\s+([a-z]+)\s+([a-z]+)", 
                r"([A-Z][a-z]+)\s+([A-Z][a-z]+)"
            ]
            
            for pattern in name_patterns:
                matches = re.findall(pattern, question, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple):
                        name = " ".join(match).title()
                    else:
                        name = match.title()
                    analysis["target_person"] = name
                    break
            
            # If no name found but it's a person query, check for specific roles
            if not analysis["target_person"]:
                if "vice-chancellor" in q_lower or "vc" in q_lower:
                    analysis["target_person"] = "Vice-Chancellor"
                elif "head" in q_lower and "department" in q_lower:
                    analysis["target_person"] = "Head of Department"
                elif "dean" in q_lower:
                    analysis["target_person"] = "Dean"
        
        # Check for department queries
        elif any(word in q_lower for word in ["department", "school", "faculty"]):
            analysis["type"] = "department_query"
            if "it" in q_lower or "information technology" in q_lower:
                analysis["target_department"] = "it"
            elif "computer science" in q_lower:
                analysis["target_department"] = "computer science"
            elif "engineering" in q_lower:
                analysis["target_department"] = "engineering"
            elif "science" in q_lower:
                analysis["target_department"] = "sciences"
        
        # Check for program/course queries
        elif any(word in q_lower for word in ["course", "program", "degree", "study", "bsc", "diploma"]):
            analysis["type"] = "academic_query"
            if "it" in q_lower or "information technology" in q_lower:
                analysis["target_program"] = "information technology"
            elif "computer science" in q_lower:
                analysis["target_program"] = "computer science"
            elif "engineering" in q_lower:
                analysis["target_program"] = "engineering"
        
        # Check for specific topics
        elif any(word in q_lower for word in ["admission", "apply", "requirement"]):
            analysis["type"] = "admission_query"
        elif any(word in q_lower for word in ["grade", "gpa", "score", "mark"]):
            analysis["type"] = "grading_query"
        elif any(word in q_lower for word in ["fee", "cost", "payment", "tuition"]):
            analysis["type"] = "financial_query"
        elif any(word in q_lower for word in ["register", "registration"]):
            analysis["type"] = "registration_query"
        elif any(word in q_lower for word in ["library", "hostel", "campus", "facility"]):
            analysis["type"] = "facility_query"
        
        return analysis

    # ---------------- INFORMATION RETRIEVAL FROM JSON ----------------
    def _search_staff_info(self, question_analysis: dict):
        """Search for staff information based on question analysis"""
        if not self.staff_data:
            return None
            
        target_person = question_analysis["target_person"]
        keywords = question_analysis["keywords"]
        matches = []
        
        # If we have a specific person name
        if target_person:
            for staff in self.staff_data:
                staff_name = staff.get("name", "").lower()
                if target_person.lower() in staff_name:
                    return self._format_staff_response(staff)
        
        # If we have keywords but no specific person
        for staff in self.staff_data:
            staff_name = staff.get("name", "").lower()
            staff_position = staff.get("current_position", "").lower()
            staff_role = staff.get("role", "").lower()
            staff_dept = staff.get("department", "").lower()
            
            # Check if any keyword matches staff information
            match_score = 0
            for keyword in keywords:
                if (keyword in staff_name or 
                    keyword in staff_position or 
                    keyword in staff_role or 
                    keyword in staff_dept):
                    match_score += 1
            
            if match_score > 0:
                matches.append((staff, match_score))
        
        # Return the best match
        if matches:
            matches.sort(key=lambda x: x[1], reverse=True)
            return self._format_staff_response(matches[0][0])
            
        return None

    def _format_staff_response(self, staff):
        """Format staff information into a readable response"""
        if not staff:
            return None
            
        response = f"{staff.get('name')} is the {staff.get('current_position')} at UENR. "
        
        if staff.get('role'):
            response += f"Their role involves {staff.get('role')}. "
        
        if staff.get('department'):
            response += f"They work in the {staff.get('department')}. "
        
        if staff.get('Education & Qualifications') and staff.get('Education & Qualifications') != "unknown":
            response += f"Qualifications: {staff.get('Education & Qualifications')}. "
        
        if staff.get('Career / Work Experience / Research Interests') and staff.get('Career / Work Experience / Research Interests') != "unknown":
            response += f"Expertise: {staff.get('Career / Work Experience / Research Interests')}. "
        
        if staff.get('achievements'):
            achievements = staff['achievements']
            if len(achievements) > 0:
                response += f"Notable achievements include: {achievements[0]}"
                if len(achievements) > 1:
                    response += f", and {len(achievements)-1} more."
            
        return response

    def _search_it_department_info(self, question_analysis: dict):
        """Search for IT department specific information"""
        if not self.it_dept_data or "department" not in self.it_dept_data:
            return None
            
        dept_info = self.it_dept_data["department"]
        response = ""
        
        # General department info
        if question_analysis["type"] == "department_query":
            response = f"The {dept_info.get('name')} is part of the {dept_info.get('school')} at UENR. "
            if dept_info.get("location"):
                response += f"It is located in {dept_info.get('location')}. "
            
            # Add staff count if available
            if dept_info.get("staff"):
                staff_count = len(dept_info["staff"])
                response += f"The department has {staff_count} staff members. "
        
        # Head of Department query
        elif question_analysis["type"] == "person_query" and ("head" in question_analysis["keywords"] or "hod" in question_analysis["keywords"]):
            hod = dept_info.get("head_of_department", {})
            if hod:
                response = f"The Head of the {dept_info.get('name')} is {hod.get('name')}. "
                response += f"They serve as {hod.get('position')} in the {hod.get('school')}."
        
        # Courses query
        elif question_analysis["type"] == "academic_query" and "course" in question_analysis["keywords"]:
            if dept_info.get("courses_offered"):
                courses = dept_info["courses_offered"]
                response = f"The {dept_info.get('name')} offers courses including: {', '.join(courses[:5])}"
                if len(courses) > 5:
                    response += f", and {len(courses)-5} more courses."
        
        # Programs query
        elif question_analysis["type"] == "academic_query" and "program" in question_analysis["keywords"]:
            if dept_info.get("programs"):
                programs = []
                for program in dept_info["programs"]:
                    programs.append(f"{program.get('degree')} in {program.get('name')} ({program.get('mode')})")
                response = f"The department offers: {', '.join(programs)}."
        
        # Staff query for IT department
        elif question_analysis["type"] == "person_query" and dept_info.get("staff"):
            target_person = question_analysis["target_person"]
            if target_person:
                for staff in dept_info["staff"]:
                    if target_person.lower() in staff.get("name", "").lower():
                        response = f"{staff.get('name')} is a {staff.get('position')} in the {dept_info.get('name')}."
                        break
        
        return response if response else None

    def _search_academic_info(self, question_analysis: dict):
        """Search for general academic information"""
        if not self.guide_data:
            return None
            
        response = ""
        q_type = question_analysis["type"]
        keywords = question_analysis["keywords"]
        
        # Programs offered
        if q_type == "academic_query" and "program" in keywords:
            programs = self.guide_data.get("Programmes_Offered", {})
            target_dept = question_analysis["target_department"] or question_analysis["target_program"]
            
            if target_dept:
                for school, program_list in programs.items():
                    school_lower = school.lower()
                    if target_dept in school_lower:
                        response = f"{school.replace('_', ' ')} offers: {', '.join(program_list[:5])}"
                        if len(program_list) > 5:
                            response += f", and {len(program_list)-5} more programs."
                        break
            else:
                # List all schools
                response = "UENR offers programs through these schools: "
                schools = []
                for school in programs.keys():
                    schools.append(school.replace('_', ' '))
                response += ", ".join(schools) + "."
            
            return response if response else None
        
        # Grading system
        elif q_type == "grading_query":
            grading = self.guide_data.get("Grading_System", {})
            if grading.get("Grades"):
                response = "UENR uses the following grading system: "
                grades = []
                for grade_info in grading["Grades"]:
                    grades.append(f"{grade_info.get('Grade')} ({grade_info.get('Mark')}) - {grade_info.get('Interpretation')}")
                response += "; ".join(grades[:3]) + "."
                return response
            return None
        
        # Course registration
        elif q_type == "registration_query":
            registration = self.guide_data.get("Course_Registration", {})
            if registration.get("Steps_to_Register"):
                response = "To register for courses at UENR: "
                steps = registration["Steps_to_Register"]
                response += " ".join(steps[:2]) + " For complete details, check the student guide."
                return response
            return None
        
        # General university info
        elif q_type == "general" or ("uenr" in keywords or "university" in keywords):
            about = self.guide_data.get("About", {})
            if about.get("Overview"):
                response = about["Overview"] + " "
            if about.get("Vision"):
                response += f"The university's vision is: {about['Vision']} "
            if about.get("Mission"):
                response += f"Its mission is: {about['Mission']}"
            return response if response else None
        
        # Location info
        elif "location" in keywords or "campus" in keywords:
            location = self.guide_data.get("Location", {})
            if location.get("Main_Campus"):
                response = f"UENR's main campus is located in {location['Main_Campus']}. "
            if location.get("Satellite_Campuses"):
                response += f"It also has satellite campuses in {', '.join(location['Satellite_Campuses'])}."
            return response if response else None
        
        return None

    # ---------------- GEMINI API CALL ----------------
    async def _call_gemini_api(self, prompt_text: str):
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt_text}]}],
            "generationConfig": {
                "temperature": 0.4,
                "maxOutputTokens": 1024,
                "topP": 0.9,
                "topK": 50,
            },
        }

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(GEMINI_API_URL, headers=headers, json=payload) as resp:
                    resp_text = await resp.text()
                    resp.raise_for_status()
                    result = json.loads(resp_text)

                    if result.get("candidates"):
                        for candidate in result["candidates"]:
                            parts = candidate.get("content", {}).get("parts", [])
                            for part in parts:
                                if "text" in part:
                                    text = part["text"].strip()
                                    if len(text) >= self.MIN_RESPONSE_LENGTH:
                                        return text[:self.MAX_RESPONSE_LENGTH]
                    return None
            except Exception as e:
                print(f"Gemini API error: {e}")
                return None

    # ---------------- MAIN INFORMATION RETRIEVAL ----------------
    def _retrieve_info(self, question: str):
        """Main method to retrieve information from all sources"""
        # Initialize data
        self._initialize_data()
        
        # Analyze question
        question_analysis = self._understand_question(question)
        
        # Try IT department specific info first (if relevant)
        if (question_analysis["target_department"] == "it" or 
            question_analysis["target_program"] == "information technology" or
            "it" in question_analysis["keywords"] or
            "information technology" in question.lower()):
            
            answer = self._search_it_department_info(question_analysis)
            if answer:
                return answer, "IT_DEPT_JSON", False
        
        # Try staff information (for person queries)
        if question_analysis["type"] == "person_query":
            answer = self._search_staff_info(question_analysis)
            if answer:
                return answer, "STAFF_JSON", False
        
        # Try academic information
        answer = self._search_academic_info(question_analysis)
        if answer:
            return answer, "GUIDE_JSON", False
        
        return None, "NONE", True

    # ---------------- ENHANCED PROMPT BUILDER ----------------
    def _build_enhanced_prompt(self, question: str, context: str = None):
        """Build a comprehensive prompt for Gemini"""
        base_prompt = (
            "You are AskUner, the official AI assistant for the University of Energy and Natural Resources (UENR) in Sunyani, Ghana. "
            "Provide accurate, helpful information about UENR. Be conversational but professional. "
            "Focus on UENR-specific information and be as detailed as possible.\n\n"
        )
        
        if context:
            base_prompt += f"Context from previous conversation: {context}\n\n"
        
        base_prompt += f"Question: {question}\n\n"
        base_prompt += (
            "Please provide a comprehensive answer about UENR. If the question is specific to "
            "a department, program, or person at UENR, focus on that aspect. Include relevant details."
        )
        
        return base_prompt

    # ---------------- POST HANDLER ----------------
    def post(self, request, *args, **kwargs):
        serializer = MessageSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        question = serializer.validated_data["question"]
        session_id = request.data.get("session_id") or str(uuid.uuid4())

        # Get previous context
        history = ChatConversation.objects.filter(session_id=session_id).order_by("created_at")
        previous_context = "\n".join([f"User: {m.question}\nBot: {m.answer}" for m in history])

        try:
            # Step 1: Try to find information in our knowledge base
            answer, source, needs_fallback = self._retrieve_info(question)

            if needs_fallback:
                # Step 2: Use Gemini with enhanced prompt
                prompt = self._build_enhanced_prompt(question, previous_context)
                ai_answer = asyncio.run(self._call_gemini_api(prompt))
                
                if ai_answer:
                    answer = ai_answer
                    source = "Gemini"
                    is_ai_augmented = True
                else:
                    # Final fallback
                    answer = (
                        "I'm still learning about that specific aspect of UENR. "
                        "For the most accurate and current information, you might want to "
                        "check the official UENR website or contact the relevant department directly."
                    )
                    source = "Fallback"
                    is_ai_augmented = False
            else:
                is_ai_augmented = False

            # Save conversation
            ChatConversation.objects.create(
                session_id=session_id,
                question=question,
                answer=answer,
                source=source,
                is_ai_augmented=is_ai_augmented,
            )

            return Response({
                "session_id": session_id,
                "answer": answer,
                "source": source,
                "is_ai_augmented": is_ai_augmented,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"AskUner Error: {e}")
            return Response(
                {"error": "Something went wrong while processing your request."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )