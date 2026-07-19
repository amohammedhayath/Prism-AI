from rest_framework import serializers
from .models import Resume, JobDescription, MatchResult, OptimizationSuggestion

# --- Utility Serializer ---
class SimpleResumeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ('id', 'candidate_name')

# --- Main Serializers ---
class ResumeSerializer(serializers.ModelSerializer):
    # Read-only fields populated by Celery/AI
    raw_text = serializers.CharField(read_only=True)
    extracted_skills = serializers.JSONField(read_only=True)
    vector_store_id = serializers.CharField(read_only=True)

    class Meta:
        model = Resume
        fields = (
            'id', 'file', 'candidate_name',
            'processing_status', 'error_message',
            'raw_text', 'extracted_skills', 'vector_store_id',
            'date_uploaded'
        )
        extra_kwargs = {
            'file': {'required': True},
            'candidate_name': {'required': False}
        }

class ResumeStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resume
        fields = ('id', 'processing_status', 'error_message')

class JobDescriptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = JobDescription
        fields = ('id', 'title', 'description', 'date_analyzed')

class MatchResultSerializer(serializers.ModelSerializer):
    resume = SimpleResumeSerializer(read_only=True)
    job_description_title = serializers.CharField(source='job_description.title', read_only=True)

    class Meta:
        model = MatchResult
        fields = (
            'id', 'fitment_score', 'justification', 'relevant_chunks',
            'resume', 'job_description_title'
        )

class OptimizationSuggestionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OptimizationSuggestion
        fields = ['id', 'original_text', 'optimized_text', 'reason', 'category', 'status']