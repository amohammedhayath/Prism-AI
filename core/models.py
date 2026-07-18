from django.db import models


class Resume(models.Model):
    # Status Choices for Celery Tracking
    STATUS_CHOICES = [
        ('PENDING', 'Pending Processing'),
        ('INDEXED', 'Indexed and Ready'),
        ('FAILED', 'Processing Failed'),
    ]

    # File and Text Storage
    file = models.FileField(upload_to='resumes/')
    raw_text = models.TextField(blank=True)

    # AI Extracted Data (Stores list of skills)
    extracted_skills = models.JSONField(default=list)

    # Structured Resume Data (JSON) & Preferred Theme
    structured_data = models.JSONField(default=dict, blank=True, null=True, help_text="Parsed resume elements")
    preferred_theme = models.CharField(max_length=50, default="Executive", help_text="Visual theme style")

    # RAG/Vector Store Reference
    vector_store_id = models.CharField(max_length=255, blank=True)

    # Metadata & Status
    candidate_name = models.CharField(max_length=255, blank=True)
    date_uploaded = models.DateTimeField(auto_now_add=True)
    processing_status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='PENDING'
    )
    error_message = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.candidate_name or 'Candidate'} - {self.processing_status}"


class JobDescription(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField()
    date_analyzed = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title


class MatchResult(models.Model):
    job_description = models.ForeignKey(JobDescription, on_delete=models.CASCADE)
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE)

    fitment_score = models.IntegerField(null=True)
    justification = models.TextField(blank=True)
    relevant_chunks = models.JSONField(default=list)

    def __str__(self):
        return f"Match: {self.resume.candidate_name} -> {self.job_description.title}"
    

class OptimizationSuggestion(models.Model):
    # Status choices for acceptance workflow
    STATUS_CHOICES = [
        ('PENDING', 'Pending Decision'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
    ]

    match_result = models.ForeignKey(MatchResult, on_delete=models.CASCADE, related_name='suggestions')
    original_text = models.TextField(help_text="The exact text from the resume")
    optimized_text = models.TextField(help_text="The AI rewritten version")
    reason = models.TextField(help_text="Why this change was made (e.g. 'Aligned with JD terminology')")
    category = models.CharField(max_length=50, default="Terminology") # e.g. "Terminology", "Impact", "Clarity"
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='PENDING', help_text="Acceptance status")

    def __str__(self):
        return f"Suggestion for Match {self.match_result.id}"