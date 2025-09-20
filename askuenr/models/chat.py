# askuenr/models/chat.py

from django.db import models

class ChatConversation(models.Model):
    """
    Stores user-bot chat messages for AskUner.
    """

    session_id = models.CharField(max_length=100, null=True, blank=True)
    question = models.TextField()
    answer = models.TextField()
    source = models.CharField(
        max_length=50,
        choices=[("JSON", "JSON"), ("Gemini", "Gemini"), ("Fallback", "Fallback")],
        default="JSON"
    )
    is_ai_augmented = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Session {self.session_id or 'Anonymous'}: {self.question[:50]}..."
