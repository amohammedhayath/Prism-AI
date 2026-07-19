# core/urls.py

from django.urls import path
from .views import (
    ResumeUploadView, 
    JobAnalysisView, 
    MatchResultView, 
    TriggerOptimizationView, 
    OptimizationResultView,
    AcceptSuggestionView,
    RejectSuggestionView,
    DownloadResumePDFView
)

urlpatterns = [
    # 1. Resume Upload
    path('resumes/upload/', ResumeUploadView.as_view(), name='resume-upload'),
    
    # 2. Job Analysis
    path('jobs/analyze/', JobAnalysisView.as_view(), name='job-analyze'),
    path('jobs/<int:job_id>/result/', MatchResultView.as_view(), name='job-result'),
    
    # 3. Optimization (The AI Enhancer)
    path('optimize/trigger/', TriggerOptimizationView.as_view(), name='optimize-trigger'),
    path('optimize/<int:match_id>/results/', OptimizationResultView.as_view(), name='optimize-results'),
    
    # 4. Accept/Reject Actions
    path('suggestions/<int:suggestion_id>/accept/', AcceptSuggestionView.as_view(), name='suggestion-accept'),
    path('suggestions/<int:suggestion_id>/reject/', RejectSuggestionView.as_view(), name='suggestion-reject'),
    
    # 5. Compile and Download PDF
    path('resumes/<int:resume_id>/download/', DownloadResumePDFView.as_view(), name='resume-download-pdf'),
]