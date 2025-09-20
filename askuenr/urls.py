# askuner_api/urls.py
from django.urls import path
from askuenr.views import AskUnerAPIView

urlpatterns = [
    path("ask/uenr/", AskUnerAPIView.as_view(), name="ask_askuner"),
]
