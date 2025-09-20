from django.contrib import admin

from askuenr.models.main import (
    University, Campus, School, Department,
    StaffProfile,
    Program, Course, AcademicRecord, GPA,
    CampusService, FeeStructure,
    NewsAndAnnouncement, Event, Scholarship,
    FAQ, ContactInfo
)
from askuenr.models.chat import ChatConversation

# Register your models here.
admin.site.register(ChatConversation)

@admin.register(University)
class UniversityAdmin(admin.ModelAdmin):
    list_display = ('name', 'established_date', 'contact_email')
    search_fields = ('name', 'contact_email')
    filter_horizontal = ()

@admin.register(Campus)
class CampusAdmin(admin.ModelAdmin):
    list_display = ('name', 'university', 'location_address')
    list_filter = ('university',)
    search_fields = ('name', 'location_address')

@admin.register(School)
class SchoolAdmin(admin.ModelAdmin):
    list_display = ('name', 'university', 'campus', 'dean')
    list_filter = ('university', 'campus')
    search_fields = ('name', 'description')
    raw_id_fields = ('dean',)

@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'school', 'head_of_department', 'office_location')
    list_filter = ('school',)
    search_fields = ('name', 'description')
    raw_id_fields = ('head_of_department',)

@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):
    list_display = ('last_name', 'first_name', 'title', 'position', 'department', 'email')
    list_filter = ('position', 'department', 'is_hod', 'is_dean')
    search_fields = ('last_name', 'first_name', 'email', 'research_interests')
    filter_horizontal = ()
    ordering = ('last_name', 'first_name')


@admin.register(Program)
class ProgramAdmin(admin.ModelAdmin):
    list_display = ('name', 'program_type', 'school', 'department', 'duration_years')
    list_filter = ('program_type', 'school', 'department')
    search_fields = ('name', 'description')
    filter_horizontal = ()
    raw_id_fields = ('program_coordinator', 'department')

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'credit_hours', 'department', 'semester_offered')
    list_filter = ('department', 'semester_offered')
    search_fields = ('code', 'title', 'description')
    filter_horizontal = ('programs', 'lecturers', 'prerequisites')
    raw_id_fields = ('department',)

@admin.register(AcademicRecord)
class AcademicRecordAdmin(admin.ModelAdmin):
    list_display = ('course', 'academic_year', 'semester', 'grade')
    list_filter = ('academic_year', 'semester', 'course')
    search_fields = ('course__code',)  # Fixed: made this a tuple
    raw_id_fields = ('course',)  # Fixed: made this a tuple



@admin.register(GPA)
class GPAAdmin(admin.ModelAdmin):
    list_display = (
        'letter_grade',
        'lower_bound',
        'upper_bound',
        'grade_point',
        'interpretation',
        'last_updated',
    )
    list_filter = ('letter_grade',)
    search_fields = ('letter_grade', 'interpretation')
    ordering = ('-upper_bound',)




@admin.register(CampusService)
class CampusServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'service_category', 'location', 'operating_hours')
    list_filter = ('service_category',)
    search_fields = ('name', 'description')
    raw_id_fields = ('service_manager',)

@admin.register(FeeStructure)
class FeeStructureAdmin(admin.ModelAdmin):
    list_display = ('fee_type', 'program', 'academic_year', 'amount', 'currency')
    list_filter = ('fee_type', 'academic_year', 'program')
    search_fields = ('program__name', 'notes')
    raw_id_fields = ('program',)

@admin.register(NewsAndAnnouncement)
class NewsAndAnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'target_audience', 'publish_date', 'author')
    list_filter = ('category', 'target_audience', 'publish_date')
    search_fields = ('title', 'content')
    raw_id_fields = ('author',)
    date_hierarchy = 'publish_date'

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'event_type', 'start_date_time', 'end_date_time', 'location', 'is_public')
    list_filter = ('event_type', 'is_public')
    search_fields = ('name', 'description', 'organizer')
    date_hierarchy = 'start_date_time'

@admin.register(Scholarship)
class ScholarshipAdmin(admin.ModelAdmin):
    list_display = ('name', 'scholarship_type', 'application_deadline', 'is_active')
    list_filter = ('scholarship_type', 'is_active')
    search_fields = ('name', 'description', 'eligibility_criteria')
    date_hierarchy = 'application_deadline'

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'category', 'last_updated')
    list_filter = ('category',)
    search_fields = ('question', 'answer')
    filter_horizontal = ('related_programs', 'related_departments')

@admin.register(ContactInfo)
class ContactInfoAdmin(admin.ModelAdmin):
    list_display = ('entity_name', 'contact_type', 'phone_number', 'email')
    list_filter = ('contact_type',)
    search_fields = ('entity_name', 'phone_number', 'email')