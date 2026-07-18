import streamlit as st
import os
import json
import pandas as pd
import tempfile
import zipfile
import io
from parsing.pdf_parser import extract_text_from_pdf
from parsing.docx_parser import extract_text_from_docx
from parsing.extractor import extract_candidate_data, load_config
from scoring.matcher import score_skills
from scoring.rules import resolve_conflicts_and_confidence
from scoring.ranker import rank_candidates

# Page Configuration
st.set_page_config(
    page_title="InternLoom Engine",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Inject design system CSS
st.markdown("""
<style>
    /* Premium Slate Background & Neutral Layout */
    .stApp {
        background-color: #f8fafc !important;
        background: #f8fafc !important;
    }
    
    /* Coherent Accent Palette (Indigo CTA buttons) */
    div.stButton > button {
        background-color: #4f46e5 !important;
        background: #4f46e5 !important;
        color: #ffffff !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.5rem 2rem !important;
        box-shadow: 0 4px 6px -1px rgba(79, 70, 229, 0.2) !important;
        transition: all 0.2s ease-in-out !important;
    }
    div.stButton > button:hover {
        background-color: #4338ca !important;
        background: #4338ca !important;
        box-shadow: 0 10px 15px -3px rgba(79, 70, 229, 0.3) !important;
        transform: translateY(-1px) !important;
    }
    
    /* Deep Slate Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f172a !important;
        background: #0f172a !important;
        color: #f8fafc !important;
    }
    [data-testid="stSidebar"] * {
        color: #f8fafc !important;
    }
    
    /* Clean Type Hierarchy & Scale */
    h1 {
        background: linear-gradient(45deg, #ff007f, #7f00ff, #00f0ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        font-size: 3rem !important;
        text-align: center;
        margin-bottom: 2rem !important;
        text-shadow: 2px 2px 8px rgba(0,0,0,0.1);
    }
    h2 {
        color: #1e293b !important;
        font-weight: 700 !important;
        font-size: 1.75rem !important;
        margin-top: 1.5rem !important;
        margin-bottom: 1rem !important;
    }
    h3, h4, h5, h6 {
        color: #1e293b !important;
        font-weight: 600 !important;
        margin-bottom: 0.5rem !important;
    }
    
    /* Body Texts & Labels Contrast */
    section[data-testid="stMain"] p,
    section[data-testid="stMain"] label,
    section[data-testid="stMain"] li,
    section[data-testid="stMain"] ul,
    section[data-testid="stMain"] ol {
        color: #334155 !important;
        font-weight: 500 !important;
        font-size: 0.95rem !important;
    }
    
    /* Cards and Containers (Neutral Slate borders) */
    div.stCard {
        background-color: #ffffff;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05), 0 1px 2px rgba(0, 0, 0, 0.06);
        border-left: 4px solid #4f46e5;
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 1rem;
    }
    div.stCard * {
        color: #334155 !important;
    }
    
    /* Clean File Uploader reset (Removes double nested borders and boxes) */
    div[data-testid*="FileUploader"] * {
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
        background-color: transparent !important;
    }
    
    /* Outermost Dropzone Card Style */
    div[data-testid*="dropzone" i] {
        background: #ffffff !important;
        background-color: #ffffff !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        transition: all 0.2s ease-in-out !important;
        padding: 1rem 1.5rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: flex-start !important;
        gap: 1rem !important;
    }
    div[data-testid*="dropzone" i]:hover {
        border-color: #4f46e5 !important;
        box-shadow: 0 4px 12px rgba(79, 70, 229, 0.08) !important;
    }
    
    /* Standardize typography inside the dropzone */
    div[data-testid*="dropzone" i] span,
    div[data-testid*="dropzone" i] p,
    div[data-testid*="dropzone" i] div {
        color: #4f46e5 !important;
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        margin: 0 !important;
        padding: 0 !important;
    }
    
    /* Styled upload button inside the dropzone */
    div[data-testid*="dropzone" i] button {
        background: #ffffff !important;
        background-color: #ffffff !important;
        color: #0f172a !important;
        font-weight: 600 !important;
        border: 1px solid #cbd5e1 !important;
        border-radius: 6px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        padding: 0.5rem 1.2rem !important;
        font-size: 0.9rem !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    div[data-testid*="dropzone" i] button:hover {
        background: #f8fafc !important;
        background-color: #f8fafc !important;
        border-color: #94a3b8 !important;
    }
    
    /* KPI Metric Cards top border */
    .stat-container {
        display: flex;
        justify-content: space-around;
        gap: 1rem;
        margin-bottom: 2rem;
    }
    .stat-card {
        flex: 1;
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        border: 1px solid #e2e8f0;
    }
    .stat-card.blue { border-top: 4px solid #3b82f6; }
    .stat-card.pink { border-top: 4px solid #ec4899; }
    .stat-card.purple { border-top: 4px solid #8b5cf6; }
    .stat-card.green { border-top: 4px solid #10b981; }
    
    .stat-val {
        font-size: 2.2rem;
        font-weight: 800;
        margin: 0.5rem 0;
    }
    .blue .stat-val { color: #2563eb; }
    .pink .stat-val { color: #db2777; }
    .purple .stat-val { color: #7c3aed; }
    .green .stat-val { color: #059669; }
    
    /* Badges */
    .badge {
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.85rem;
        font-weight: 600;
        display: inline-block;
    }
    .badge-clean { background-color: #d1fae5; color: #065f46; }
    .badge-partial { background-color: #fef3c7; color: #92400e; }
    .badge-failed { background-color: #fee2e2; color: #991b1b; }
    
    /* Compact Dataframe font size and cell sizing */
    div[data-testid="stDataFrame"] *, div[data-testid="stTable"] * {
        font-size: 0.82rem !important;
    }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>InternLoom Engine</h1>", unsafe_allow_html=True)

role_display_names = {
    "frontend_developer": "Frontend Developer",
    "backend_developer": "Backend Developer",
    "full_stack_developer": "Full Stack Developer",
    "database_developer": "Database Developer",
    "api_integration_developer": "API Integration Developer"
}

config = load_config()
synonyms_map = config.get("synonyms", {})
weights_config = config.get("weights", {})
default_jds = config.get("default_job_descriptions", {})

# Mode Selection tabs at the page level (No emoji)
app_mode = st.tabs(["Shortlist Engine", "Role Recommender"])

def parse_file_like(file_obj, filename):
    """
    Saves a file-like object to a temporary location and parses it.
    Returns: (text, parse_status, reason)
    """
    ext = os.path.splitext(filename)[1].lower()
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as temp_file:
        temp_file.write(file_obj.read())
        temp_path = temp_file.name
        
    try:
        if ext == '.pdf':
            text, status, reason = extract_text_from_pdf(temp_path)
        elif ext == '.docx':
            text, status, reason = extract_text_from_docx(temp_path)
        elif ext == '.txt':
            try:
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    text = f.read()
                status, reason = "Clean", "Parsed successfully"
            except Exception as e:
                text, status, reason = "", "Failed", f"Text file read error: {str(e)}"
        elif ext == '.xml':
            try:
                with open(temp_path, 'r', encoding='utf-8', errors='ignore') as f:
                    xml_content = f.read()
                import re
                text = re.sub(r'<[^>]+>', ' ', xml_content)
                text = re.sub(r'\s+', ' ', text).strip()
                status, reason = "Clean", "Parsed successfully"
            except Exception as e:
                text, status, reason = "", "Failed", f"XML parse error: {str(e)}"
        elif ext == '.doc':
            text, status, reason = "", "Failed", "Unsupported legacy format: .doc. Please convert to PDF or DOCX."
        else:
            text, status, reason = "", "Failed", f"Unsupported file format '{ext}'."
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
            
    return text, status, reason

def parse_uploaded_file(uploaded_file):
    return parse_file_like(uploaded_file, uploaded_file.name)

# ----------------- MODE 1: Bulk Shortlisting -----------------
with app_mode[0]:
    st.header("Candidate Shortlisting Engine")
    st.markdown("Batch evaluate multiple uploaded resumes against target job descriptions.")
    
    # Group related inputs in a bordered container
    with st.container(border=True):
        st.subheader("Configure Evaluation Parameters")
        
        # User-friendly display names for selection
        selected_role_display = st.selectbox("Select Target Role", list(role_display_names.values()))
        # Resolve to internal role ID
        selected_role_name = [k for k, v in role_display_names.items() if v == selected_role_display][0]
        jd_info = default_jds[selected_role_name]
        
        col1, col2 = st.columns(2)
        with col1:
            cutoff = st.slider("Min Suitability Score Cutoff", 30, 90, 50, 5)
        with col2:
            slots = st.slider("Target Slots (Max Shortlisted)", 1, 30, jd_info.get("slots", 5))
            
        jd_info["slots"] = slots
        
        # Replace folder path text input with file uploader
        uploaded_files = st.file_uploader(
            "Upload Resumes", type=["pdf", "docx", "zip", "txt", "xml"], accept_multiple_files=True
        )
        
        # Trigger button inside the panel
        run_btn = st.button("Run Shortlisting")
        
    if run_btn:
        if not uploaded_files:
            st.error("Please upload one or more resumes or a zip folder to evaluate.")
        else:
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            # Expand zip files if present
            expanded_files = []
            for uploaded_file in uploaded_files:
                filename = uploaded_file.name
                if filename.lower().endswith('.zip'):
                    try:
                        zip_bytes = uploaded_file.read()
                        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                            for zinfo in z.infolist():
                                if zinfo.is_dir():
                                    continue
                                zname = os.path.basename(zinfo.filename)
                                if not zname or zname.startswith('.') or zname.startswith('~'):
                                    continue
                                ext = os.path.splitext(zname)[1].lower()
                                if ext in ['.pdf', '.docx', '.doc', '.txt', '.xml']:
                                    file_bytes = z.read(zinfo.filename)
                                    expanded_files.append((zname, io.BytesIO(file_bytes)))
                    except Exception as e:
                        st.error(f"Error reading zip file {filename}: {str(e)}")
                else:
                    expanded_files.append((filename, uploaded_file))
            
            if not expanded_files:
                st.error("No valid resumes (.pdf, .docx, .doc, .txt, .xml) found in the uploads.")
            else:
                all_extracted_candidates = []
                parse_quality_data = {}
                
                total_files = len(expanded_files)
                for idx, (filename, file_obj) in enumerate(expanded_files):
                    status_text.text(f"Parsing ({idx+1}/{total_files}): {filename}...")
                    
                    # Parse using temporary file helper
                    text, parse_status, reason = parse_file_like(file_obj, filename)
                        
                    cand = extract_candidate_data(text, parse_status, reason)
                    cand["filename"] = filename
                    cand["raw_text"] = text
                    
                    all_extracted_candidates.append(cand)
                    parse_quality_data[filename] = {
                        "parse_status": parse_status,
                        "parse_reason": reason
                    }
                    
                    progress_bar.progress((idx + 1) / total_files)
                    
                status_text.text("Extraction complete. Scoring candidates...")
                
                # Match & Score
                evaluated_candidates = []
                for cand in all_extracted_candidates:
                    if cand["parse_status"] == "Failed":
                        cand["score"] = None
                        cand["confidence"] = "Low"
                        cand["reasoning"] = [
                            "Parsing failed completely. File could not be processed.",
                            "Requires manual review.",
                            f"Error details: {cand['parse_reason']}"
                        ]
                        evaluated_candidates.append(cand)
                        continue
                        
                    skill_score, matched_details = score_skills(
                        candidate_skills=cand["skills"],
                        required_skills=jd_info.get("required_skills", []),
                        preferred_skills=jd_info.get("preferred_skills", []),
                        synonyms_map=synonyms_map,
                        candidate_text=cand["raw_text"],
                        weights_config=weights_config
                    )
                    
                    final_score, confidence, reasoning = resolve_conflicts_and_confidence(
                        candidate_data=cand,
                        skill_score=skill_score,
                        matched_details=matched_details
                    )
                    
                    cand["score"] = final_score
                    cand["confidence"] = confidence
                    cand["reasoning"] = reasoning
                    cand["matched_skills_breakdown"] = matched_details
                    evaluated_candidates.append(cand)
                    
                # Ranking
                ranking_results = rank_candidates(
                    candidates_results=evaluated_candidates,
                    slots=jd_info.get("slots", 5),
                    min_cgpa=jd_info.get("min_cgpa", 0.0),
                    cutoff_score=cutoff
                )
                
                # Display Statistics Cards
                shortlist_cnt = len(ranking_results["shortlist"])
                reserve_cnt = len(ranking_results["reserve_list"])
                failed_cnt = len(ranking_results["failed_list"])
                
                st.markdown(f"""
                <div class="stat-container">
                    <div class="stat-card blue">
                        <div>Evaluated</div>
                        <div class="stat-val">{total_files}</div>
                    </div>
                    <div class="stat-card green">
                        <div>Shortlisted</div>
                        <div class="stat-val">{shortlist_cnt}</div>
                    </div>
                    <div class="stat-card purple">
                        <div>Reserve List</div>
                        <div class="stat-val">{reserve_cnt}</div>
                    </div>
                    <div class="stat-card pink">
                        <div>Failed Parse</div>
                        <div class="stat-val">{failed_cnt}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Tabs for results (No emojis)
                tab1, tab2, tab3, tab4 = st.tabs(["Ranked Shortlist", "Reserve List", "Unqualified Candidates", "Parse Review Queue"])
                
                with tab1:
                    st.subheader(f"Ranked Shortlist (Top {slots} Slots)")
                    if not ranking_results["shortlist"]:
                        st.info("No candidates qualified for the shortlist.")
                    else:
                        df_data = []
                        for idx, c in enumerate(ranking_results["shortlist"], 1):
                            df_data.append({
                                "Rank": idx,
                                "Name": c["name"],
                                "Score (/100)": c["score"],
                                "Confidence": c["confidence"],
                                "CGPA": c["cgpa"],
                                "Email": c["email"],
                                "Reasoning": " | ".join(c["reasoning"])
                            })
                        st.table(pd.DataFrame(df_data).set_index("Rank"))
                        
                with tab2:
                    st.subheader("Reserve Candidates")
                    if not ranking_results["reserve_list"]:
                        st.info("No candidates in the reserve list.")
                    else:
                        df_data = []
                        for idx, c in enumerate(ranking_results["reserve_list"], 1):
                            df_data.append({
                                "Rank": slots + idx,
                                "Name": c["name"],
                                "Score (/100)": c["score"],
                                "Confidence": c["confidence"],
                                "CGPA": c["cgpa"],
                                "Email": c["email"],
                                "Points Below Shortlist": f"{c.get('points_below_shortlist', 0.0)} pts",
                                "Reasoning": " | ".join(c["reasoning"]),
                                "Status Reason": "Qualified, but exceeded available slots (Ranked below top N)"
                            })
                        st.table(pd.DataFrame(df_data).set_index("Rank"))
                        
                with tab3:
                    st.subheader("Unqualified Candidates")
                    if not ranking_results["unqualified_list"]:
                        st.success("No unqualified candidates.")
                    else:
                        df_data = []
                        for idx, c in enumerate(ranking_results["unqualified_list"], 1):
                            df_data.append({
                                "S.No": idx,
                                "Name": c.get("name") or "Unknown Candidate",
                                "Score (/100)": c.get("score") if c.get("score") is not None else "N/A",
                                "CGPA": c.get("cgpa") if c.get("cgpa") is not None else "N/A",
                                "Email": c.get("email") or "N/A",
                                "Disqualification Reason": c.get("disqualification_reason", "Below score cutoff")
                            })
                        st.table(pd.DataFrame(df_data).set_index("S.No"))
                        
                with tab4:
                    st.subheader("Failed Parse List (Immediate Human Review Required)")
                    if not ranking_results["failed_list"]:
                        st.success("No file parsing failures encountered.")
                    else:
                        df_data = []
                        for idx, c in enumerate(ranking_results["failed_list"], 1):
                            df_data.append({
                                "S.No": idx,
                                "File Name": c.get("filename", "Unknown"),
                                "Status": c["parse_status"],
                                "Failure Reason": c.get("parse_reason", "N/A"),
                                "Recommendation": "Requires Manual Review"
                             })
                        st.table(pd.DataFrame(df_data).set_index("S.No"))
                        
                # Export CSV Button
                all_scored = ranking_results["shortlist"] + ranking_results["reserve_list"]
                if all_scored:
                    export_df = pd.DataFrame([{
                        "Name": c["name"],
                        "Email": c["email"],
                        "Phone": c["phone"],
                        "College": c["college"],
                        "Degree": c["degree"],
                        "Branch": c["branch"],
                        "CGPA": c["cgpa"],
                        "Score": c["score"],
                        "Confidence": c["confidence"],
                        "Status": "Shortlisted" if c in ranking_results["shortlist"] else "Reserve"
                    } for c in all_scored])
                    
                    csv_data = export_df.to_csv(index=False).encode('utf-8')
                    st.download_button(
                        label="Export Shortlist & Reserve List to CSV",
                        data=csv_data,
                        file_name="internloom_shortlist_export.csv",
                        mime="text/csv"
                    )

# ----------------- MODE 2: Role Recommender -----------------
with app_mode[1]:
    st.header("Role Recommender (Reverse Matcher)")
    st.markdown("Upload your resume and find your most suitable career path among all job descriptions.")
    
    uploaded_resume = st.file_uploader("Upload Resumes", type=["pdf", "docx", "zip", "txt", "xml"])
    
    if uploaded_resume is not None:
        if st.button("Find Best Role"):
            with st.spinner("Processing..."):
                filename = uploaded_resume.name
                expanded_files = []
                if filename.lower().endswith('.zip'):
                    try:
                        zip_bytes = uploaded_resume.read()
                        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                            for zinfo in z.infolist():
                                if zinfo.is_dir():
                                    continue
                                zname = os.path.basename(zinfo.filename)
                                if not zname or zname.startswith('.') or zname.startswith('~'):
                                    continue
                                ext = os.path.splitext(zname)[1].lower()
                                if ext in ['.pdf', '.docx', '.doc', '.txt', '.xml']:
                                    file_bytes = z.read(zinfo.filename)
                                    expanded_files.append((zname, io.BytesIO(file_bytes)))
                    except Exception as e:
                        st.error(f"Error reading zip file: {str(e)}")
                else:
                    expanded_files.append((filename, uploaded_resume))
                
                if not expanded_files:
                    st.error("No valid resumes found in the upload.")
                else:
                    for zname, file_obj in expanded_files:
                        text, parse_status, reason = parse_file_like(file_obj, zname)
                        if parse_status == "Failed":
                            st.error(f"Failed to parse {zname}: {reason}")
                            continue
                            
                        cand = extract_candidate_data(text, parse_status, reason)
                        cand["raw_text"] = text
                        
                        st.markdown(f"### Candidate Profile Parsed: **{cand['name']}** ({zname})")
                        
                        # Show parsed details inside a bright card
                        st.markdown(f"""
                        <div class="stCard">
                          <h4>Profile Summary</h4>
                          <ul>
                              <li><b>College:</b> {cand['college'] or 'Not detected'}</li>
                              <li><b>Degree & Branch:</b> {cand['degree'] or ''} {cand['branch'] or ''}</li>
                              <li><b>Graduation Year:</b> {cand['graduation_year'] or 'Not detected'}</li>
                              <li><b>CGPA Normalised:</b> {cand['cgpa'] or 'Not detected'} / 10.0 ({cand['grade_assumption']})</li>
                              <li><b>Identified Skills ({len(cand['skills'])}):</b> {', '.join(cand['skills'])}</li>
                          </ul>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # Score against all 5 preloaded JDs
                        role_scores = []
                        for role_id, jd in default_jds.items():
                            skill_score, matched_details = score_skills(
                                candidate_skills=cand["skills"],
                                required_skills=jd.get("required_skills", []),
                                preferred_skills=jd.get("preferred_skills", []),
                                synonyms_map=synonyms_map,
                                candidate_text=cand["raw_text"],
                                weights_config=weights_config
                            )
                            
                            final_score, confidence, reasoning = resolve_conflicts_and_confidence(
                                candidate_data=cand,
                                skill_score=skill_score,
                                matched_details=matched_details
                            )
                            
                            role_scores.append({
                                "Role ID": role_id,
                                "Role Name": jd["role"],
                                "Matching Score": final_score,
                                "Confidence": confidence,
                                "Reasoning": reasoning,
                                "Breakdown": matched_details
                            })
                            
                        # Sort descending by score
                        role_scores.sort(key=lambda x: x["Matching Score"], reverse=True)
                        
                        # Display Role Suitability
                        st.markdown("#### Role Suitability Leaderboard")
                        best_role = role_scores[0]
                        st.success(f"💡 Recommended Role: **{best_role['Role Name']}** (Score: {best_role['Matching Score']}/100)")
                        
                        for idx, r in enumerate(role_scores[:3], 1):
                            score_val = r["Matching Score"]
                            st.markdown(f"**{idx}. {r['Role Name']}** — **{score_val}/100**")
                            st.progress(score_val / 100.0)
                            
                            bullets_html = "".join([f"<li>{b}</li>" for b in r["Reasoning"]])
                            st.markdown(f"""
                            <ul>
                                {bullets_html}
                            </ul>
                            """, unsafe_allow_html=True)
                        st.write("---")
