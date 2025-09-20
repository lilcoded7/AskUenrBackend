from rest_framework import serializers

class MessageSerializer(serializers.Serializer):
    """
    Serializer for incoming user messages/questions.
    """
    question = serializers.CharField(max_length=1000)

class ResponseSerializer(serializers.Serializer):
    """
    Serializer for the AI's response.
    """
    answer = serializers.CharField()
    
