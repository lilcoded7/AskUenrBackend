import json
from django.core.management.base import BaseCommand
from askuenr.models.main import GPA

GPA_BANDS = [
    {
        "lower_bound": 80,
        "upper_bound": 100,
        "letter_grade": "A",
        "grade_point": 4.00,
        "interpretation": "Excellent"
    },
    {
        "lower_bound": 75,
        "upper_bound": 79,
        "letter_grade": "B+",
        "grade_point": 3.50,
        "interpretation": "Very Good"
    },
    {
        "lower_bound": 70,
        "upper_bound": 74,
        "letter_grade": "B",
        "grade_point": 3.00,
        "interpretation": "Good"
    },
    {
        "lower_bound": 65,
        "upper_bound": 69,
        "letter_grade": "C+",
        "grade_point": 2.50,
        "interpretation": "Fair"
    },
    {
        "lower_bound": 60,
        "upper_bound": 64,
        "letter_grade": "C",
        "grade_point": 2.00,
        "interpretation": "Satisfactory"
    },
    {
        "lower_bound": 55,
        "upper_bound": 59,
        "letter_grade": "D+",
        "grade_point": 1.50,
        "interpretation": "Pass"
    },
    {
        "lower_bound": 50,
        "upper_bound": 54,
        "letter_grade": "D",
        "grade_point": 1.00,
        "interpretation": "Barely Pass"
    },
    {
        "lower_bound": 0,
        "upper_bound": 49,
        "letter_grade": "F",
        "grade_point": 0.00,
        "interpretation": "Fail"
    }
]

class Command(BaseCommand):
    help = "Seeds GPA bands and prints them as JSON."

    def handle(self, *args, **options):
        GPA.objects.all().delete()

        for band in GPA_BANDS:
            GPA.objects.create(
                lower_bound=band["lower_bound"],
                upper_bound=band["upper_bound"],
                letter_grade=band["letter_grade"],
                grade_point=band["grade_point"],
                interpretation=band["interpretation"]
            )
        
        all_gpas = GPA.objects.all().values(
            'lower_bound',
            'upper_bound',
            'letter_grade',
            'grade_point',
            'interpretation'
        )

        gpa_list = []
        for item in all_gpas:
            item['grade_point'] = float(item['grade_point'])
            gpa_list.append(item)

        json_output = json.dumps(gpa_list, indent=4)
        
        self.stdout.write(self.style.SUCCESS("GPA bands saved successfully."))
        self.stdout.write(json_output)
