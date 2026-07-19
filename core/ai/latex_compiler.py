# core/ai/latex_compiler.py

import os
import re
import subprocess
import tempfile
import shutil

# --- Helper: Safe LaTeX Escaping ---
def escape_latex(text):
    if text is None:
        return ""
    if not isinstance(text, str):
        text = str(text)
    # Map special LaTeX syntax symbols to their escaped versions
    # Backslash must be escaped first or in a single pass to avoid double-escaping backslashes introduced by other replacements
    replacements = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    # Regular expression to match any of the keys
    pattern = re.compile('|'.join(re.escape(key) for key in replacements.keys()))
    return pattern.sub(lambda match: replacements[match.group(0)], text)


# --- 1. Executive / Minimal LaTeX Template (0.5in Margins, Tight Gaps) ---
EXECUTIVE_TEMPLATE = r"""
\documentclass[letterpaper,11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.5in]{geometry}
\usepackage{titlesec}
\usepackage{enumitem}

\titleformat{\section}{\large\bfseries\scshape}{}{0em}{}[\titlerule]
\titlespacing{\section}{0pt}{6pt}{3pt}

\pagestyle{empty}
\pagenumbering{gobble}

\begin{document}

\begin{center}
    {\Huge \bfseries <<NAME>>} \\ \vspace{2pt}
    \small <<CONTACT_LINE>>
\end{center}

\vspace{-10pt}

% --- SUMMARY ---
<<SUMMARY_SECTION>>

% --- EXPERIENCE ---
\section{Professional Experience}
\begin{itemize}[leftmargin=0in, label={}]
<<EXPERIENCE_BLOCKS>>
\end{itemize}

% --- PROJECTS ---
<<PROJECTS_SECTION>>

% --- EDUCATION ---
\section{Education}
\begin{itemize}[leftmargin=0in, label={}]
<<EDUCATION_BLOCKS>>
\end{itemize}

% --- SKILLS ---
\section{Skills}
<<SKILLS_LIST>>

\end{document}
"""


# --- 2. Sleek Tech LaTeX Template (0.5in Margins, Sans-serif, Tight Gaps) ---
TECH_TEMPLATE = r"""
\documentclass[letterpaper,11pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.5in]{geometry}
\usepackage{titlesec}
\usepackage{enumitem}
\usepackage{xcolor}

\definecolor{techblue}{HTML}{0ea5e9} % Slate Cyan/Sky Blue Highlight

\titleformat{\section}{\large\bfseries\color{techblue}}{}{0em}{}[\titlerule]
\titlespacing{\section}{0pt}{6pt}{3pt}

\pagestyle{empty}
\pagenumbering{gobble}
\renewcommand{\familydefault}{\sfdefault} % Set default to beautiful Sans-Serif

\begin{document}

\noindent
{\Huge \bfseries <<NAME>>} \\
\textcolor{gray}{\small <<CONTACT_LINE>>}

\vspace{5pt}

% --- SUMMARY ---
<<SUMMARY_SECTION>>

% --- EXPERIENCE ---
\section{Experience}
\begin{itemize}[leftmargin=0in, label={}]
<<EXPERIENCE_BLOCKS>>
\end{itemize}

% --- PROJECTS ---
<<PROJECTS_SECTION>>

% --- EDUCATION ---
\section{Education}
\begin{itemize}[leftmargin=0in, label={}]
<<EDUCATION_BLOCKS>>
\end{itemize}

% --- SKILLS ---
\section{Technical Expertise}
<<SKILLS_LIST>>

\end{document}
"""


# --- 3. Academic / CV LaTeX Template (0.5in Margins, Traditional, Tight Gaps) ---
ACADEMIC_TEMPLATE = r"""
\documentclass[letterpaper,10pt]{article}
\usepackage[utf8]{inputenc}
\usepackage[margin=0.5in]{geometry}
\usepackage{titlesec}
\usepackage{enumitem}

\titleformat{\section}{\normalsize\bfseries\uppercase}{}{0em}{}[\titlerule]
\titlespacing{\section}{0pt}{8pt}{4pt}

\pagestyle{empty}
\pagenumbering{gobble}

\begin{document}

\noindent
{\huge \bfseries <<NAME>>} \\
\small <<CONTACT_LINE>>

\vspace{6pt}

% --- SUMMARY ---
<<SUMMARY_SECTION>>

% --- EDUCATION ---
\section{Education}
\begin{itemize}[leftmargin=0in, label={}]
<<EDUCATION_BLOCKS>>
\end{itemize}

% --- EXPERIENCE ---
\section{Professional Appointments \& Research}
\begin{itemize}[leftmargin=0in, label={}]
<<EXPERIENCE_BLOCKS>>
\end{itemize}

% --- PROJECTS ---
<<PROJECTS_SECTION>>

% --- SKILLS ---
\section{Technical Competencies}
<<SKILLS_LIST>>

\end{document}
"""


# --- The Central Compiler Engine ---
def compile_latex_to_pdf(structured_data, theme="Executive"):
    # Select template based on chosen theme
    if theme == "Tech":
        template = TECH_TEMPLATE
    elif theme == "Academic":
        template = ACADEMIC_TEMPLATE
    else:
        template = EXECUTIVE_TEMPLATE

    # 1. Escape LaTeX characters for all parsed fields
    name = escape_latex(structured_data.get("name", "Candidate"))
    contact = structured_data.get("contact", {})
    email = escape_latex(contact.get("email", ""))
    phone = escape_latex(contact.get("phone", ""))
    location = escape_latex(contact.get("location", ""))
    linkedin = escape_latex(contact.get("linkedin", ""))

    # Build contact line dynamically (Removes double minus bars!)
    contact_parts = []
    if email:
        contact_parts.append(email)
    if phone:
        contact_parts.append(phone)
    if location:
        contact_parts.append(location)
    if linkedin:
        contact_parts.append(linkedin)
    
    contact_line = " \\ | \\ ".join(contact_parts)

    # 2. Build Summary Section if present (Tighter vertical bounds)
    summary_text = structured_data.get("summary", "")
    summary_section = ""
    if summary_text and summary_text.strip():
        summary_escaped = escape_latex(summary_text)
        if theme == "Academic":
            summary_section = f"\\section{{Research Statement \\& Profile}}\n{summary_escaped}\n\\vspace{{1pt}}\n"
        else: # Tech or Executive
            summary_section = f"\\section{{Professional Summary}}\n{summary_escaped}\n\\vspace{{1pt}}\n"

    # 3. Build Experience LaTeX blocks (Ultra-tight list padding)
    experience_list = structured_data.get("experience", [])
    exp_blocks = []
    for exp in experience_list:
        comp = escape_latex(exp.get("company", ""))
        role = escape_latex(exp.get("role", ""))
        date = escape_latex(exp.get("date", ""))
        bullets = exp.get("bullets", [])
        
        bullet_items = "\n".join([f"    \\item {escape_latex(b)}" for b in bullets])
        
        block = f"""\\item 
    \\textbf{{{role}}} \\hfill {date} \\\\
    \\textit{{{comp}}}
    \\begin{{itemize}}[leftmargin=0.15in, topsep=1pt, itemsep=1pt, parsep=0pt, partopsep=0pt, label=\\textbullet]
{bullet_items}
    \\end{{itemize}}
    \\vspace{{2pt}}"""
        exp_blocks.append(block)
    
    experience_latex = "\n".join(exp_blocks)

    # 4. Build Projects Section if present (Tighter lists, circle bullets)
    projects_list = structured_data.get("projects", [])
    projects_section = ""
    if projects_list:
        proj_blocks = []
        for proj in projects_list:
            title = escape_latex(proj.get("title", ""))
            date = escape_latex(proj.get("date", ""))
            desc = proj.get("description", "")
            
            # Format description into clean professional bullet lists
            if desc:
                # Split description by period followed by space, or newline
                sentences = [s.strip() for s in re.split(r'\n|\.\s+', desc) if s.strip()]
                cleaned_bullets = []
                for s in sentences:
                    if s and not s.endswith('.'):
                        s += '.'
                    cleaned_bullets.append(s)
                
                bullet_items = "\n".join([f"        \\item {escape_latex(b)}" for b in cleaned_bullets])
                block = f"""\\item 
    \\textbf{{{title}}} \\hfill {date}
    \\begin{{itemize}}[leftmargin=0.15in, topsep=1pt, itemsep=1pt, parsep=0pt, partopsep=0pt, label=\\textbullet]
{bullet_items}
    \\end{{itemize}}
    \\vspace{{2pt}}"""
            else:
                block = f"""\\item 
    \\textbf{{{title}}} \\hfill {date}
    \\vspace{{2pt}}"""
            
            proj_blocks.append(block)
        
        proj_latex = "\n".join(proj_blocks)
        
        projects_section = f"""\\section{{Projects}}
\\begin{{itemize}}[leftmargin=0in, label={{}}]
{proj_latex}
\\end{{itemize}}
\\vspace{{1pt}}"""

    # 5. Build Education LaTeX blocks
    education_list = structured_data.get("education", [])
    edu_blocks = []
    for edu in education_list:
        inst = escape_latex(edu.get("institution", ""))
        deg = escape_latex(edu.get("degree", ""))
        date = escape_latex(edu.get("date", ""))
        
        block = f"""\\item 
    \\textbf{{{inst}}} \\hfill {date} \\\\
    \\textit{{{deg}}} \\vspace{{2pt}}"""
        edu_blocks.append(block)
    
    education_latex = "\n".join(edu_blocks)

    # 6. Build Categorized Skills Rows dynamically
    skills_raw = structured_data.get("skills", [])
    
    languages = []
    frameworks = []
    databases = []
    tools = []
    
    for s in skills_raw:
        s_esc = escape_latex(s)
        s_lower = s.lower().strip()
        
        # Bucket skills based on keyword matching
        if any(x in s_lower for x in ["python", "java", "javascript", "html", "css", "c++", "c#", "typescript"]):
            if "react" in s_lower or "api" in s_lower:
                frameworks.append(s_esc)
            else:
                languages.append(s_esc)
        elif any(x in s_lower for x in ["react", "fastapi", "django", "flask", "ui development", "bootstrap", "tailwind"]):
            frameworks.append(s_esc)
        elif any(x in s_lower for x in ["postgresql", "mysql", "sqlite", "sql", "orm", "database"]):
            databases.append(s_esc)
        else:
            tools.append(s_esc)

    skills_lines = []
    if languages:
        skills_lines.append(f"\\textbf{{Programming Languages:}} " + " $\\cdot$ ".join(languages))
    if frameworks:
        skills_lines.append(f"\\textbf{{Frameworks \\& Libraries:}} " + " $\\cdot$ ".join(frameworks))
    if databases:
        skills_lines.append(f"\\textbf{{Databases \\& Storage:}} " + " $\\cdot$ ".join(databases))
    if tools:
        skills_lines.append(f"\\textbf{{Tools \\& Technologies:}} " + " $\\cdot$ ".join(tools))
    
    skills_latex = " \\\\ \n".join(skills_lines)

    # 7. Inject actual values into LaTeX template
    full_latex_code = template
    full_latex_code = full_latex_code.replace("<<NAME>>", name)
    full_latex_code = full_latex_code.replace("<<CONTACT_LINE>>", contact_line)
    full_latex_code = full_latex_code.replace("<<SUMMARY_SECTION>>", summary_section)
    full_latex_code = full_latex_code.replace("<<EXPERIENCE_BLOCKS>>", experience_latex)
    full_latex_code = full_latex_code.replace("<<PROJECTS_SECTION>>", projects_section)
    full_latex_code = full_latex_code.replace("<<EDUCATION_BLOCKS>>", education_latex)
    full_latex_code = full_latex_code.replace("<<SKILLS_LIST>>", skills_latex)

    # 8. Compile LaTeX locally in a safe, temporary directory
    temp_dir = tempfile.mkdtemp()
    tex_path = os.path.join(temp_dir, "resume.tex")
    pdf_path = os.path.join(temp_dir, "resume.pdf")

    # Safe dynamic output directory resolution
    from django.conf import settings
    output_dir = os.path.join(settings.BASE_DIR, "generated_resumes")
    os.makedirs(output_dir, exist_ok=True)

    try:
        # Write .tex file
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(full_latex_code)

        # Debug: Save generated LaTeX code to generated_resumes/ for verification
        try:
            debug_tex_path = os.path.join(output_dir, "generated_resume_10.tex")
            with open(debug_tex_path, "w", encoding="utf-8") as debug_f:
                debug_f.write(full_latex_code)
        except Exception:
            pass

        # Run pdflatex command directly inside the temp directory
        cmd = [
            "pdflatex", 
            "-interaction=nonstopmode", 
            "-halt-on-error", 
            "resume.tex"
        ]
        
        # Run command inside temp_dir with 15-second timeout
        try:
            res = subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True, check=True, timeout=15)
        except subprocess.CalledProcessError as sub_err:
            # Save the generated failing LaTeX code to the workspace so we can inspect it!
            try:
                failed_tex_path = os.path.join(output_dir, "failed_resume.tex")
                with open(failed_tex_path, "w", encoding="utf-8") as debug_f:
                    debug_f.write(full_latex_code)
                
                temp_log_path = os.path.join(temp_dir, "resume.log")
                if os.path.exists(temp_log_path):
                    shutil.copy(temp_log_path, os.path.join(output_dir, "failed_resume.log"))
            except Exception:
                pass

            # Combine console output and stderr for maximum diagnostic details
            console_out = (sub_err.stdout or "") + " | " + (sub_err.stderr or "")
            clean_console = " | ".join([line.strip() for line in console_out.split('\n') if line.strip()])
            
            log_path = os.path.join(temp_dir, "resume.log")
            log_content = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as log_f:
                    log_content = log_f.read()
            # Get the last 15 lines of the compiler log to capture the exact trace
            log_lines = log_content.split('\n')
            last_lines = " | ".join([line.strip() for line in log_lines[-15:] if line.strip()])
            
            raise Exception(f"pdflatex failed. Console: {clean_console[:250]} | Log: {last_lines[:250]}")

        # Read the generated PDF binary data
        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        try:
            # Copy success files to output directory for debugging/verification in the workspace
            shutil.copy(pdf_path, os.path.join(output_dir, "generated_resume_10.pdf"))
            temp_log_path = os.path.join(temp_dir, "resume.log")
            if os.path.exists(temp_log_path):
                shutil.copy(temp_log_path, os.path.join(output_dir, "generated_resume_10.log"))
        except Exception:
            pass

        return pdf_bytes

    finally:
        # Clean up temporary compile files to keep server tidy
        shutil.rmtree(temp_dir)
