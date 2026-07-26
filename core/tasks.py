import os
import json
import chromadb
from celery import shared_task
from django.conf import settings
from .models import Resume, JobDescription, MatchResult, OptimizationSuggestion
from .ai.agent import get_genai_client
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# --- CONFIGURATION ---
# Initialize ChromaDB
chroma_client = chromadb.PersistentClient(path="chroma_db")
collection = chroma_client.get_or_create_collection(name="resume_embeddings")


# --- TASK 1: PROCESS RESUME ---
@shared_task
def process_resume_task(resume_id):
    try:
        print(f"Starting processing for Resume ID: {resume_id}")
        resume = Resume.objects.get(id=resume_id)
        
        client = get_genai_client()
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # 1. Read PDF file as inline bytes
        with open(resume.file.path, 'rb') as f:
            pdf_bytes = f.read()

        pdf_part = types.Part.from_bytes(
            data=pdf_bytes,
            mime_type='application/pdf'
        )

        # 2. Extract Complete Structured Resume & Auto-Detect Theme
        print("Parsing resume into clean structured JSON and detecting layout theme via Gemini...")
        prompt = """
        Analyze this resume PDF and parse it into a structured JSON format. 
        Additionally, analyze the vocabulary, style, and structure of the candidate's resume and auto-detect which visual theme fits their style best:
        - "Executive" (Formal, single-column, traditional, corporate-focused)
        - "Tech" (Modern, sans-serif, technology-focused, crisp layout)
        - "Academic" (Compact, publication/CV layout, research and education focused)

        Output ONLY a valid JSON object matching the following structure:
        {
            "name": "Candidate Full Name",
            "contact": {
                "email": "email address",
                "phone": "phone number",
                "location": "city, country",
                "linkedin": "linkedin url if exists"
            },
            "summary": "Candidate's professional summary or profile statement if exists, otherwise leave blank",
            "skills": ["Skill 1", "Skill 2"],
            "education": [
                {
                    "institution": "University/School name",
                    "degree": "Degree earned",
                    "date": "Year or date range"
                }
            ],
            "experience": [
                {
                    "company": "Company Name",
                    "role": "Job Title/Role",
                    "date": "Date range",
                    "bullets": [
                        "Accomplishment bullet point 1",
                        "Accomplishment bullet point 2"
                    ]
                }
            ],
            "projects": [
                {
                    "title": "Project Name",
                    "date": "Project date range or completion year",
                    "description": "Short description of what the project is, goals, or technologies used"
                }
            ],
            "detected_theme": "Executive" or "Tech" or "Academic"
        }
        """

        response = client.models.generate_content(
            model=model_name,
            contents=[prompt, pdf_part],
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        
        # Parse the JSON response
        parsed_data = json.loads(response.text)
        
        # Save JSON data and the detected theme to our database
        resume.structured_data = parsed_data
        resume.preferred_theme = parsed_data.get("detected_theme", "Executive")
        resume.candidate_name = parsed_data.get("name", "Candidate")
        
        # Store extracted skills separately for backwards compatibility
        resume.extracted_skills = parsed_data.get("skills", [])

        # 3. Extract Full Raw Text
        print("Extracting raw text for RAG chunking...")
        text_response = client.models.generate_content(
            model=model_name,
            contents=[
                "Extract all raw text content from this resume PDF. Maintain hierarchy and clean structure.",
                pdf_part
            ]
        )
        full_text = text_response.text
        resume.raw_text = full_text

        # 4. Generate Embeddings (Text-Embedding-004) in Batch
        chunks = [c for c in full_text.split('\n\n') if c.strip()]
        print(f"Generating embeddings for {len(chunks)} chunks in a single batch request...")

        if chunks:
            # Batch generate all embeddings in ONE single API call!
            embedding_resp = client.models.embed_content(
                model='text-embedding-004',
                contents=chunks,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT"
                )
            )
            
            # Save all chunks to ChromaDB
            for i, chunk in enumerate(chunks):
                embedding = embedding_resp.embeddings[i].values
                collection.add(
                    ids=[f"resume_{resume.id}_chunk_{i}"],
                    embeddings=[embedding],
                    documents=[chunk],
                    metadatas=[{"resume_id": str(resume.id)}]
                )

        resume.vector_store_id = f"resume_{resume.id}"
        resume.processing_status = 'INDEXED'
        resume.save()
        print(f"Resume {resume_id} processed and indexed successfully!")

    except Exception as e:
        print(f"Error processing resume: {e}")
        try:
            resume = Resume.objects.get(id=resume_id)
            resume.processing_status = 'FAILED'
            resume.save()
        except Exception as inner_err:
            print(f"Failed to update model status: {inner_err}")


# --- TASK 2: ANALYZE JOB MATCH ---
@shared_task
def analyze_job_match_task(job_id, resume_id):
    try:
        print(f"Starting analysis for Job {job_id} vs Resume {resume_id}...")

        # 1. Fetch Data
        job = JobDescription.objects.get(id=job_id)
        resume = Resume.objects.get(id=resume_id)

        if not resume.vector_store_id:
            print("Error: Resume not indexed.")
            return

        client = get_genai_client()
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # 2. Convert Job Description to Vector
        embedding_resp = client.models.embed_content(
            model='text-embedding-004',
            contents=job.description,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY"
            )
        )
        query_embedding = embedding_resp.embeddings[0].values

        # 3. Search ChromaDB
        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=3,
            where={"resume_id": str(resume.id)}
        )

        documents = results.get('documents', [])
        if not documents or not documents[0]:
            print("No relevant chunks found.")
            relevant_chunks = ["No specific match found in resume."]
        else:
            relevant_chunks = documents[0]

        print(f"Found {len(relevant_chunks)} relevant chunks.")

        # 4. AI Analysis (Structured JSON)
        context_text = "\n".join(relevant_chunks)
        prompt = f"""
        You are an expert HR AI. Compare the following Candidate Context against the Job Description.

        JOB DESCRIPTION:
        {job.description}

        CANDIDATE RELEVANT EXPERIENCE:
        {context_text}

        TASK:
        1. Assign a fitment score (0-100).
        2. Write a 2-sentence justification explaining the score.

        OUTPUT FORMAT (JSON only):
        {{
            "score": 85,
            "justification": "The candidate has..."
        }}
        """

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        try:
            analysis_data = json.loads(response.text)
        except Exception as json_err:
            cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
            analysis_data = json.loads(cleaned_text)

        # 5. Save Results
        MatchResult.objects.create(
            job_description=job,
            resume=resume,
            fitment_score=analysis_data.get('score'),
            justification=analysis_data.get('justification'),
            relevant_chunks=relevant_chunks
        )

        print(f"Analysis Complete! Score: {analysis_data.get('score')}")
        return "Match Analysis Succeeded"

    except Exception as e:
        print(f"Analysis Failed: {str(e)}")
        return f"Failed: {str(e)}"


# --- TASK 3: GENERATE OPTIMIZATION SUGGESTIONS ---
@shared_task
def generate_optimization_task(match_id):
    try:
        print(f"Starting Optimization for Match ID: {match_id}")
        match = MatchResult.objects.get(id=match_id)
        job = match.job_description
        resume = match.resume

        client = get_genai_client()
        model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        # 1. Construct the Context-Aware Prompt
        resume_context = "\n".join(match.relevant_chunks)

        prompt = f"""
        Act as an Expert Technical Resume Writer. Your goal is "Semantic Alignment."
        
        CONTEXT:
        A candidate applied for a job but used generic terms. You must rewrite their bullet points to use the specific professional terminology found in the Job Description, without inventing new skills.

        JOB DESCRIPTION:
        {job.description}

        CANDIDATE'S CURRENT RESUME SNIPPETS:
        {resume_context}

        TASK:
        Identify 3 specific bullet points or sentences from the Candidate's snippets that can be improved.
        For each, rewrite it to adopt the specific vocabulary/keywords from the Job Description.
        
        RULES:
        1. Do NOT invent skills the candidate didn't mention.
        2. Keep the rewritten version concise and professional.
        3. Explain strictly WHY you changed it (e.g., "Mapped generic 'database' to specific 'PostgreSQL' from JD").

        OUTPUT FORMAT (Strict JSON List):
        [
            {{
                "original_text": "text from resume",
                "optimized_text": "rewritten text with JD keywords",
                "reason": "explanation",
                "category": "Terminology"
            }}
        ]
        """

        # 2. Call Gemini (Structured JSON)
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        # 3. Clean and parse JSON
        try:
            suggestions = json.loads(response.text)
        except Exception as json_err:
            cleaned_text = response.text.strip().replace('```json', '').replace('```', '')
            suggestions = json.loads(cleaned_text)

        # 4. Save to Database
        OptimizationSuggestion.objects.filter(match_result=match).delete()

        for item in suggestions:
            OptimizationSuggestion.objects.create(
                match_result=match,
                original_text=item.get('original_text'),
                optimized_text=item.get('optimized_text'),
                reason=item.get('reason'),
                category=item.get('category', 'Terminology')
            )
        
        print(f"Optimization Complete. Saved {len(suggestions)} suggestions.")
        return "Optimization Succeeded"

    except Exception as e:
        print(f"Optimization Failed: {str(e)}")
        return f"Failed: {str(e)}"