import json
from django.core.management.base import BaseCommand
from django.core.serializers.json import DjangoJSONEncoder
from askuenr.models.main import GPA  # Replace 'your_app' with your actual app name

class Command(BaseCommand):
    help = 'Load UENR grading system data into the database and export as JSON'

    def handle(self, *args, **options):
        # UENR grading system data
        grading_data = [
            {
                'lower_bound': 80,
                'upper_bound': 100,
                'letter_grade': 'A',
                'grade_point': 4.00,
                'interpretation': 'Excellent'
            },
            {
                'lower_bound': 75,
                'upper_bound': 79,
                'letter_grade': 'B+',
                'grade_point': 3.50,
                'interpretation': 'Very Good'
            },
            {
                'lower_bound': 70,
                'upper_bound': 74,
                'letter_grade': 'B',
                'grade_point': 3.00,
                'interpretation': 'Good'
            },
            {
                'lower_bound': 65,
                'upper_bound': 69,
                'letter_grade': 'C+',
                'grade_point': 2.50,
                'interpretation': 'Fairly Good'
            },
            {
                'lower_bound': 60,
                'upper_bound': 64,
                'letter_grade': 'C',
                'grade_point': 2.00,
                'interpretation': 'Average'
            },
            {
                'lower_bound': 55,
                'upper_bound': 59,
                'letter_grade': 'D+',
                'grade_point': 1.50,
                'interpretation': 'Below Average'
            },
            {
                'lower_bound': 50,
                'upper_bound': 54,
                'letter_grade': 'D',
                'grade_point': 1.00,
                'interpretation': 'Marginal Pass'
            },
            {
                'lower_bound': 0,
                'upper_bound': 49,
                'letter_grade': 'F',
                'grade_point': 0.00,
                'interpretation': 'Fail'
            }
        ]

        # Clear existing data
        GPA.objects.all().delete()
        self.stdout.write(self.style.SUCCESS('Deleted existing GPA data'))

        # Load new data
        created_count = 0
        for grade in grading_data:
            GPA.objects.create(
                lower_bound=grade['lower_bound'],
                upper_bound=grade['upper_bound'],
                letter_grade=grade['letter_grade'],
                grade_point=grade['grade_point'],
                interpretation=grade['interpretation']
            )
            created_count += 1

        self.stdout.write(self.style.SUCCESS(f'Successfully created {created_count} GPA records'))

        # Export to JSON
        export_data = {
            'grading_system': grading_data,
            'semesters': ['Harmattan', 'Rain', 'Summer']
        }

        json_output = json.dumps(export_data, indent=2, cls=DjangoJSONEncoder)
        self.stdout.write("\nJSON Output:\n")
        self.stdout.write(json_output)

        # Optionally save to file
        with open('uenr_grading_system.json', 'w') as f:
            json.dump(export_data, f, indent=2)
        self.stdout.write(self.style.SUCCESS('\nData also saved to uenr_grading_system.json'))