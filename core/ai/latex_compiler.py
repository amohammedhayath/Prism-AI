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
    pattern = re.compile('|'.join(re.escape(key) for key in replacements.keys()))
    return pattern.sub(lambda match: replacements[match.group(0)], text)


# --- 1. Executive / Minimal LaTeX Template ---
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
<<EXPERIENCE_SECTION>>

% --- PROJECTS ---
<<PROJECTS_SECTION>>

% --- EDUCATION ---
<<EDUCATION_SECTION>>

% --- SKILLS ---
<<SKILLS_SECTION>>

\end{document}
"""


# --- 2. Sleek Tech LaTeX Template ---
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
\renewcommand{\familydefault}{\sfdefault}

\begin{document}

\noindent
{\Huge \bfseries <<NAME>>} \\
\textcolor{gray}{\small <<CONTACT_LINE>>}

\vspace{5pt}

% --- SUMMARY ---
<<SUMMARY_SECTION>>

% --- EXPERIENCE ---
<<EXPERIENCE_SECTION>>

% --- PROJECTS ---
<<PROJECTS_SECTION>>

% --- EDUCATION ---
<<EDUCATION_SECTION>>

% --- SKILLS ---
<<SKILLS_SECTION>>

\end{document}
"""


# --- 3. Academic / CV LaTeX Template ---
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
<<EDUCATION_SECTION>>

% --- EXPERIENCE ---
<<EXPERIENCE_SECTION>>

% --- PROJECTS ---
<<PROJECTS_SECTION>>

% --- SKILLS ---
<<SKILLS_SECTION>>

\end{document}
"""


# --- The Central Compiler Engine ---
def compile_latex_to_pdf(structured_data, theme="Executive"):
    if theme == "Tech":
        template = TECH_TEMPLATE
    elif theme == "Academic":
        template = ACADEMIC_TEMPLATE
    else:
        template = EXECUTIVE_TEMPLATE

    # 1. Header Contact Line
    name = escape_latex(structured_data.get("name", "Candidate"))
    contact = structured_data.get("contact", {})
    email = escape_latex(contact.get("email", ""))
    phone = escape_latex(contact.get("phone", ""))
    location = escape_latex(contact.get("location", ""))
    linkedin = escape_latex(contact.get("linkedin", ""))

    contact_parts = [p for p in [email, phone, location, linkedin] if p]
    contact_line = " \\ | \\ ".join(contact_parts)

    # 2. Summary Section
    summary_text = structured_data.get("summary", "")
    summary_section = ""
    if summary_text and summary_text.strip():
        summary_escaped = escape_latex(summary_text)
        sec_title = "Research Statement \\& Profile" if theme == "Academic" else "Professional Summary"
        summary_section = f"\\section{{{sec_title}}}\n{summary_escaped}\n\\vspace{{1pt}}\n"

    # 3. Experience Section
    experience_list = structured_data.get("experience", [])
    experience_section = ""
    if experience_list:
        exp_blocks = []
        for exp in experience_list:
            comp = escape_latex(exp.get("company", ""))
            role = escape_latex(exp.get("role", ""))
            date = escape_latex(exp.get("date", ""))
            bullets = exp.get("bullets", [])

            valid_bullets = [escape_latex(b) for b in bullets if b and str(b).strip()]
            
            if valid_bullets:
                bullet_items = "\n".join([f"    \\item {b}" for b in valid_bullets])
                bullet_block = f"""\\begin{{itemize}}[leftmargin=0.15in, topsep=1pt, itemsep=1pt, parsep=0pt, partopsep=0pt, label=\\textbullet]
{bullet_items}
\\end{{itemize}}"""
            else:
                bullet_block = ""

            block = f"""\\item 
    \\textbf{{{role}}} \\hfill {date} \\\\
    \\textit{{{comp}}}
{bullet_block}
    \\vspace{{2pt}}"""
            exp_blocks.append(block)

        sec_header = "Professional Appointments \\& Research" if theme == "Academic" else ("Experience" if theme == "Tech" else "Professional Experience")
        exp_latex = "\n".join(exp_blocks)
        experience_section = f"""\\section{{{sec_header}}}
\\begin{{itemize}}[leftmargin=0in, label={{}}]
{exp_latex}
\\end{{itemize}}
\\vspace{{1pt}}"""

    # 4. Projects Section
    projects_list = structured_data.get("projects", [])
    projects_section = ""
    if projects_list:
        proj_blocks = []
        for proj in projects_list:
            title = escape_latex(proj.get("title", ""))
            date = escape_latex(proj.get("date", ""))
            desc = proj.get("description", "")

            if desc:
                sentences = [s.strip() for s in re.split(r'\n|\.\s+', str(desc)) if s.strip()]
                cleaned_bullets = [s if s.endswith('.') else s + '.' for s in sentences]
                valid_proj_bullets = [escape_latex(b) for b in cleaned_bullets if b]

                if valid_proj_bullets:
                    bullet_items = "\n".join([f"        \\item {b}" for b in valid_proj_bullets])
                    bullet_block = f"""\\begin{{itemize}}[leftmargin=0.15in, topsep=1pt, itemsep=1pt, parsep=0pt, partopsep=0pt, label=\\textbullet]
{bullet_items}
\\end{{itemize}}"""
                else:
                    bullet_block = ""

                block = f"""\\item 
    \\textbf{{{title}}} \\hfill {date}
{bullet_block}
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

    # 5. Education Section
    education_list = structured_data.get("education", [])
    education_section = ""
    if education_list:
        edu_blocks = []
        for edu in education_list:
            inst = escape_latex(edu.get("institution", ""))
            deg = escape_latex(edu.get("degree", ""))
            date = escape_latex(edu.get("date", ""))

            block = f"""\\item 
    \\textbf{{{inst}}} \\hfill {date} \\\\
    \\textit{{{deg}}} \\vspace{{2pt}}"""
            edu_blocks.append(block)

        edu_latex = "\n".join(edu_blocks)
        education_section = f"""\\section{{Education}}
\\begin{{itemize}}[leftmargin=0in, label={{}}]
{edu_latex}
\\end{{itemize}}
\\vspace{{1pt}}"""

    # 6. Skills Section
    skills_raw = structured_data.get("skills", [])
    skills_section = ""
    if skills_raw:
        languages, frameworks, databases, tools = [], [], [], []

        for s in skills_raw:
            s_esc = escape_latex(s)
            s_lower = str(s).lower().strip()

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

        if skills_lines:
            skills_latex = " \\\\ \n".join(skills_lines)
            sec_title = "Technical Expertise" if theme == "Tech" else ("Technical Competencies" if theme == "Academic" else "Skills")
            skills_section = f"\\section{{{sec_title}}}\n{skills_latex}"

    # 7. Substitute Into Template
    full_latex_code = template
    full_latex_code = full_latex_code.replace("<<NAME>>", name)
    full_latex_code = full_latex_code.replace("<<CONTACT_LINE>>", contact_line)
    full_latex_code = full_latex_code.replace("<<SUMMARY_SECTION>>", summary_section)
    full_latex_code = full_latex_code.replace("<<EXPERIENCE_SECTION>>", experience_section)
    full_latex_code = full_latex_code.replace("<<PROJECTS_SECTION>>", projects_section)
    full_latex_code = full_latex_code.replace("<<EDUCATION_SECTION>>", education_section)
    full_latex_code = full_latex_code.replace("<<SKILLS_SECTION>>", skills_section)

    # 8. Compile via pdflatex
    temp_dir = tempfile.mkdtemp()
    tex_path = os.path.join(temp_dir, "resume.tex")
    pdf_path = os.path.join(temp_dir, "resume.pdf")

    try:
        with open(tex_path, "w", encoding="utf-8") as f:
            f.write(full_latex_code.replace("\r", ""))

        cmd = [
            "pdflatex",
            "-interaction=nonstopmode",
            "-halt-on-error",
            "resume.tex"
        ]

        try:
            subprocess.run(cmd, cwd=temp_dir, capture_output=True, text=True, check=True, timeout=15)
        except subprocess.CalledProcessError as sub_err:
            console_out = (sub_err.stdout or "") + " | " + (sub_err.stderr or "")
            clean_console = " | ".join([line.strip() for line in console_out.split('\n') if line.strip()])

            log_path = os.path.join(temp_dir, "resume.log")
            log_content = ""
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as log_f:
                    log_content = log_f.read()
            log_lines = log_content.split('\n')
            last_lines = " | ".join([line.strip() for line in log_lines[-15:] if line.strip()])

            raise Exception(f"pdflatex failed. Console: {clean_console[:250]} | Log: {last_lines[:250]}")

        with open(pdf_path, "rb") as f:
            pdf_bytes = f.read()

        return pdf_bytes

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
