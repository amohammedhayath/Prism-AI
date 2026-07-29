# core/views.py

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Resume, JobDescription, MatchResult, OptimizationSuggestion
from .serializers import (
    ResumeSerializer, 
    MatchResultSerializer, 
    OptimizationSuggestionSerializer
)
# We import the Async Tasks
from .tasks import process_resume_task, analyze_job_match_task, generate_optimization_task
from django.http import HttpResponse
from .ai.latex_compiler import compile_latex_to_pdf

# --- 1. Upload Resume ---
class ResumeUploadView(APIView):
    def post(self, request):
        serializer = ResumeSerializer(data=request.data)
        if serializer.is_valid():
            resume = serializer.save()
            # Trigger Celery Task to process PDF
            process_resume_task.delay(resume.id)
            return Response({"id": resume.id, "message": "Upload successful"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# --- 2. Job Analysis (RENAMED TO MATCH URLS) ---
class JobAnalysisView(APIView):
    def post(self, request):
        resume_id = request.data.get('resume_id')
        title = request.data.get('title', 'General Role')
        description = request.data.get('description')

        if not resume_id or not description:
            return Response({"error": "Resume ID and Job Description are required"}, status=status.HTTP_400_BAD_REQUEST)

        # Create Job Record
        job = JobDescription.objects.create(
            title=title,
            description=description
        )

        # Trigger Celery Task for Analysis
        analyze_job_match_task.delay(job.id, resume_id)

        return Response({
            "job_id": job.id, 
            "status": "PROCESSING"
        }, status=status.HTTP_202_ACCEPTED)

# --- 3. Match Result ---
class MatchResultView(APIView):
    def get(self, request, job_id):
        try:
            match = MatchResult.objects.get(job_description_id=job_id)
            return Response({
                "match_id": match.id,
                "score": match.fitment_score,
                "justification": match.justification,
                "status": "COMPLETED"
            }, status=status.HTTP_200_OK)
        except MatchResult.DoesNotExist:
            return Response({"status": "PENDING"}, status=status.HTTP_200_OK)

# --- 4. Optimization Trigger ---
class TriggerOptimizationView(APIView):
    def post(self, request):
        match_id = request.data.get('match_id')
        if not match_id:
            return Response({"error": "match_id required"}, status=status.HTTP_400_BAD_REQUEST)
        
        # Trigger Celery Task
        generate_optimization_task.delay(match_id)
        
        return Response({"message": "Optimization started", "status": "PROCESSING"}, status=status.HTTP_202_ACCEPTED)

# --- 5. Optimization Result ---
class OptimizationResultView(APIView):
    def get(self, request, match_id):
        suggestions = OptimizationSuggestion.objects.filter(match_result_id=match_id)
        
        if not suggestions.exists():
             return Response({"status": "PENDING", "data": []}, status=status.HTTP_200_OK)
        
        serializer = OptimizationSuggestionSerializer(suggestions, many=True)
        return Response({
            "status": "COMPLETED", 
            "data": serializer.data
        }, status=status.HTTP_200_OK)


# --- 6. Accept Suggestion ---
class AcceptSuggestionView(APIView):
    def post(self, request, suggestion_id):
        try:
            suggestion = OptimizationSuggestion.objects.get(id=suggestion_id)
            if suggestion.status == 'ACCEPTED':
                return Response({"message": "Already accepted"}, status=status.HTTP_400_BAD_REQUEST)

            match = suggestion.match_result
            resume = match.resume

            # 1. Update status to ACCEPTED
            suggestion.status = 'ACCEPTED'
            suggestion.save()

            # 2. Update the structured JSON data inside Resume
            structured_data = resume.structured_data or {}
            
            from difflib import SequenceMatcher

            # Recursive helper using difflib to find and replace text with robust fuzzy-matching (80%+ threshold)
            def replace_text_in_json(data, target, replacement):
                target_stripped = target.strip()
                target_clean = target_stripped.lower()
                if not target_clean:
                    return
                if isinstance(data, dict):
                    for k, v in data.items():
                        if isinstance(v, (dict, list)):
                            replace_text_in_json(v, target, replacement)
                        elif isinstance(v, str):
                            # 1. Precise case-insensitive substring replace (preserves wrapper context)
                            idx = v.lower().find(target_clean)
                            if idx != -1:
                                start_idx = idx
                                end_idx = idx + len(target_clean)
                                data[k] = v[:start_idx] + replacement + v[end_idx:]
                            else:
                                # 2. Fallback: Fuzzy-match the entire string
                                v_clean = v.strip().lower()
                                ratio = SequenceMatcher(None, v_clean, target_clean).ratio()
                                if ratio >= 0.8:
                                    data[k] = replacement
                elif isinstance(data, list):
                    for i, item in enumerate(data):
                        if isinstance(item, (dict, list)):
                            replace_text_in_json(item, target, replacement)
                        elif isinstance(item, str):
                            # 1. Precise case-insensitive substring replace (preserves wrapper context)
                            idx = item.lower().find(target_clean)
                            if idx != -1:
                                start_idx = idx
                                end_idx = idx + len(target_clean)
                                data[i] = item[:start_idx] + replacement + item[end_idx:]
                            else:
                                # 2. Fallback: Fuzzy-match the entire string
                                item_clean = item.strip().lower()
                                ratio = SequenceMatcher(None, item_clean, target_clean).ratio()
                                if ratio >= 0.8:
                                    data[i] = replacement

            # Replace the original_text bullet point with optimized_text
            replace_text_in_json(structured_data, suggestion.original_text, suggestion.optimized_text)
            
            # Save the updated JSON back to the Resume model
            resume.structured_data = structured_data
            resume.save()

            return Response({"status": "ACCEPTED", "message": "Resume updated with accepted suggestion!"}, status=status.HTTP_200_OK)

        except OptimizationSuggestion.DoesNotExist:
            return Response({"error": "Suggestion not found"}, status=status.HTTP_404_NOT_FOUND)


# --- 7. Reject Suggestion ---
class RejectSuggestionView(APIView):
    def post(self, request, suggestion_id):
        try:
            suggestion = OptimizationSuggestion.objects.get(id=suggestion_id)
            suggestion.status = 'REJECTED'
            suggestion.save()
            return Response({"status": "REJECTED", "message": "Suggestion rejected"}, status=status.HTTP_200_OK)
        except OptimizationSuggestion.DoesNotExist:
            return Response({"error": "Suggestion not found"}, status=status.HTTP_404_NOT_FOUND)


# --- 8. Compile and Download PDF ---
# class DownloadResumePDFView(APIView):
#     def get(self, request, resume_id):
#         try:
#             resume = Resume.objects.get(id=resume_id)
            
#             if not resume.structured_data:
#                 return Response({"error": "No structured resume data found. Please wait until upload is fully indexed."}, status=status.HTTP_400_BAD_REQUEST)

#             # Read theme from query parameters (e.g. ?theme=Tech) or fallback to saved preference
#             selected_theme = request.query_params.get('theme', resume.preferred_theme)
            
#             # Save selection as preferred theme
#             if selected_theme != resume.preferred_theme:
#                 resume.preferred_theme = selected_theme
#                 resume.save()

#             print(f"Compiling resume {resume_id} using theme: {selected_theme}...")
            
#             # Run our compilation pipeline
#             pdf_bytes = compile_latex_to_pdf(resume.structured_data, selected_theme)

#             # Return binary stream directly to client
#             response = HttpResponse(pdf_bytes, content_type='application/pdf')
#             filename = f"{resume.candidate_name.replace(' ', '_')}_Resume.pdf"
#             response['Content-Disposition'] = f'attachment; filename="{filename}"'
#             response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
#             response['Pragma'] = 'no-cache'
#             response['Expires'] = '0'
#             return response

#         except Resume.DoesNotExist:
#             return Response({"error": "Resume not found"}, status=status.HTTP_404_NOT_FOUND)
#         except Exception as err:
#             return Response({"error": f"Failed to compile LaTeX PDF: {err}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class DownloadResumePDFView(APIView):
    def get(self, request, resume_id):
        try:
            resume = Resume.objects.get(id=resume_id)
            
            if not resume.structured_data:
                return Response(
                    {"error": "No structured resume data found. Please wait until upload is fully indexed."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            selected_theme = request.query_params.get('theme', resume.preferred_theme)
            
            if selected_theme != resume.preferred_theme:
                resume.preferred_theme = selected_theme
                resume.save()

            print(f"Compiling resume {resume_id} using theme: {selected_theme}...")
            
            pdf_bytes = compile_latex_to_pdf(resume.structured_data, selected_theme)

            # Sanitize candidate name for header safety
            candidate_name = getattr(resume, 'candidate_name', 'Upgraded') or 'Upgraded'
            safe_filename = f"{candidate_name.replace(' ', '_')}_Resume.pdf"

            response = HttpResponse(pdf_bytes, content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="{safe_filename}"'
            # Expose header so Axios in React can access Content-Disposition
            response['Access-Control-Expose-Headers'] = 'Content-Disposition'
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
            return response

        except Resume.DoesNotExist:
            return Response({"error": "Resume not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as err:
            return Response({"error": f"Failed to compile LaTeX PDF: {err}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
