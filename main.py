import streamlit as st
import streamlit.components.v1 as components
import json, re
from processing import summarize_youtube_video, segment_transcript, evaluate_officer_behavior

outputs_dir = "assets/"

st.set_page_config(page_title="Video Review - Officer Excellence in Action", layout="wide")
st.image("img/benchmark_logo.png", width=300)
st.title("Video Review - Officer Excellence in Action")
st.caption("Select an officer and choose a body-worn camera video from an incident. Once the video is transcribed, our system will analyze the transcript and highlight key moments that demonstrate excellence across five performance domains. Use this tool to recognize outstanding conduct, identify coaching opportunities, and support ongoing professional development through real-world examples.")

tabs = st.tabs(["👮 Officer Summary", "📺 Manage Videos", "➕ Add New Video"])
# Load existing data or initialize a new dictionary
def load_data():
    try:
        with open(f'{outputs_dir}officers_data.json', 'r') as file:
            data = json.load(file)
    except FileNotFoundError:
        data = {}
    return data

# Save the data back to a JSON file
def save_data(data):
    with open(f'{outputs_dir}officers_data.json', 'w') as file:
        json.dump(data, file, indent=4)

with tabs[0]:
    st.subheader("Officer Behavior Summary")
    st.caption("Select an officer to review a summary of behavior evaluations across all uploaded videos, categorized by performance area.")
    officer_data = load_data()


    show_descriptions = st.toggle("Show Excellence Domain Descriptions")

    if show_descriptions:
        try:
            with open("extras/domain_descriptions.json", "r") as f:
                descriptions = json.load(f)
            st.markdown("### 📘 Excellence Domain Descriptions")
            for cat, desc in descriptions.items():
                with st.expander(cat):
                    st.markdown(desc)
        except FileNotFoundError:
            st.error("Excellence Domain Descriptions file not found. Please ensure it's in the correct directory.")

    col1, col2 = st.columns([1, 2])
    with col1:

        summary_officer_name = st.selectbox("Select Officer", options=[""] + list(officer_data.keys()), key="summary_select")

        # Domains and Subdomains
        domain_subdomains = {
            "Maximum Engagement": ["Calls for Service", "Arrests", "Time to Engage", "Self-initiated / Proactive"],
            "Minimal Harm": ["Officer Injury Avoidance", "Citizen Injury Avoidance", "External Complaint Reduction", "Citizen Recognition"],
            "Disciplined Conduct": ["Attendance", "Infractions", "Accidents"],
            "Team Player": ["Showing Up First", "Showing Up for Team", "Balance of Call Types"],
            "Skillful Actions": ["Time to Resolve", "De-escalation", "Force Avoidance"]
        }

        selected_domain = st.selectbox("Select Domain (Required)", [""] + list(domain_subdomains.keys()))
        selected_subdomains = []

        if selected_domain:
            selected_subdomains = st.multiselect(
                "Select Subdomains (Required)",
                options=domain_subdomains[selected_domain]
            )

    with col2:
        if summary_officer_name and selected_domain and selected_subdomains:
            evaluations = []

            for video in officer_data.get(summary_officer_name, []):
                evaluation = video.get("evaluation", "")
                if evaluation:
                    lines = evaluation.splitlines()
                    current_eval = {}
                    all_evals = []

                    for line in lines:
                        if line.startswith("**Domain**:"):
                            current_eval["domain"] = line.replace("**Domain**:", "").strip()
                        elif line.startswith("**Subdomain**:"):
                            current_eval["subdomain"] = line.replace("**Subdomain**:", "").strip()
                        elif line.startswith("**Quote**:"):
                            current_eval["quote"] = line.replace("**Quote**:", "").strip()
                        elif line.startswith("**Summary**:"):
                            current_eval["summary"] = line.replace("**Summary**:", "").strip()
                        elif line.startswith("**Reference**:"):
                            current_eval["reference"] = line.replace("**Reference**:", "").strip()
                            all_evals.append(current_eval)
                            current_eval = {}

                    for ev in all_evals:
                        if ev["domain"] == selected_domain and ev["subdomain"] in selected_subdomains:
                            match = re.search(r'\((.*?)\)', ev['reference'])
                            if match:
                                timing = match.group(1).split('-')[0].strip().replace('s', '')
                            else:
                                timing = "0" # fallback
                            summary_text = (
                                f"**Quote**: \"{ev['quote']}\"\n\n"
                                f"**Summary**: {ev['summary']}\n\n"
                                f"**Reference**: {ev['reference']}"
                            )
                            evaluations.append({
                                "subdomain": ev["subdomain"],
                                "title": video["title"],
                                "summary": summary_text,
                                "video": video["url"],
                                "start_time": timing
                            })

            if evaluations:
                st.markdown(f"### 🏅 {selected_domain}")
                for eval_entry in evaluations:
                    with st.expander(f"📹 {eval_entry['title']} — {eval_entry['subdomain']}", expanded=False):
                        st.markdown(f"**Subdomain**: {eval_entry['subdomain']}")
                        st.markdown(f"**Video Title**: {eval_entry['title']}")
                        st.markdown(eval_entry['summary'])

                        video_url = eval_entry['video']
                        start_time = eval_entry.get("start_time", "0")  # fallback
                        st.markdown(f"**Reference Video**:")
                        components.html(
                            f"""
                            <div style="text-align:left;">
                                <iframe width="700" height="380"
                                src="{video_url.replace('watch?v=', 'embed/')}?start={start_time}"
                                frameborder="0" allowfullscreen></iframe>
                            </div>
                            """,
                            height=400
                        )
            else:
                st.info("No evaluations match the selected subdomains.")
        elif summary_officer_name and (not selected_domain or not selected_subdomains):
            st.warning("Please select both a domain and at least one subdomain to view evaluations.")


with tabs[1]:
    officer_data = load_data()
    st.subheader("Manage Officer Video and Generate Insights")
    st.caption("Use this tab to select an officer, view their body cam footage, generate transcripts, segment dialogue, and evaluate behavior—all in one streamlined workflow with data saved automatically.")

    officer_name = st.selectbox("Select Officer", options=[""] + list(officer_data.keys()))

    selected_video_url = ""
    selected_video_transcript = ""
    selected_video_segments = ""
    selected_video_evaluation = ""

    if officer_name:
        if officer_data.get(officer_name):
            video_titles = [f"{video['title']} - {video['url']}" for video in officer_data[officer_name]]
            selected_video = st.selectbox("Select Video", options=[""] + video_titles)

            selected_video_entry = next(
                (video for video in officer_data[officer_name]
                 if f"{video['title']} - {video['url']}" == selected_video),
                None
            )

            if selected_video_entry:
                selected_video_url = selected_video_entry.get('url', '')
                selected_video_transcript = selected_video_entry.get('transcript', '')
                selected_video_segments = selected_video_entry.get('segments', '')
                selected_video_evaluation = selected_video_entry.get('evaluation', '')

    if selected_video_url:
        col1, col2 = st.columns([1.3, 1.7])

        with col1:
            components.html(
                f"""
                <div style="text-align:left;">
                    <iframe width="700px" height="480"
                    src="{selected_video_url.replace("watch?v=", "embed/")}"
                    frameborder="0" allowfullscreen></iframe>
                </div>
                """,
                height=500
            )

        with col2:
            if selected_video_transcript:
                formatted_transcript = "\n".join(selected_video_transcript)

                with st.expander("📝 Existing Transcript", expanded=False):
                    st.text_area(
                        "*Transcripts are generated by Artificial Intelligence. You may directly edit copy to ensure the transcript matches with the observed behavior.",
                        formatted_transcript,
                        height=280
                    )

                if selected_video_segments:
                    with st.expander("🧩 Segmented Transcript", expanded=False):
                        st.text_area(
                            "*Segments are generated by Artificial Intelligence. You may directly edit copy to ensure the summarized segments match with the observed behavior.",
                            selected_video_segments,
                            height=280
                        )

                    if selected_video_evaluation:
                        with st.expander("🔍 Officer Behavior Evaluation", expanded=False):
                            st.text_area(
                                "*Evaluations are generated by Artificial Intelligence. You may directly edit copy to ensure the summary matches with the observed behavior.",
                                selected_video_evaluation,
                                height=280
                            )
                    else:
                        if st.button("Evaluate Officer Behavior"):
                            with st.spinner("Evaluating officer behavior..."):
                                evaluation = evaluate_officer_behavior(selected_video_segments)
                                with st.expander("🔍 Officer Behavior Evaluation", expanded=False):
                                    st.text_area("Evaluation", evaluation, height=300)
                                for video in officer_data[officer_name]:
                                    if video['url'] == selected_video_url:
                                        video['evaluation'] = evaluation
                                        break
                                save_data(officer_data)
                                st.rerun()

                else:
                    if st.button("Segment Transcript"):
                        with st.spinner("Segmenting transcript..."):
                            segments = segment_transcript(selected_video_transcript)
                            with st.expander("🧩 Segmented Transcript", expanded=False):
                                st.text_area(
                                    "*Segments are generated by Artificial Intelligence. You may directly edit copy to ensure the summarized segments match with the observed behavior.",
                                    segments,
                                    height=280
                                )
                            for video in officer_data[officer_name]:
                                if video['url'] == selected_video_url:
                                    video['segments'] = segments
                                    break
                            save_data(officer_data)
                            st.rerun()

            else:
                if st.button("Generate Transcript"):
                    with st.spinner("Transcripting... Please wait."):
                        transcriptions = summarize_youtube_video(selected_video_url, outputs_dir)
                        with st.expander("📝 Existing Transcript", expanded=False):
                            st.text_area(
                                "*Transcripts are generated by Artificial Intelligence. You may directly edit copy to ensure the transcript matches with the observed behavior.",
                                transcriptions,
                                height=280
                            )
                        for video in officer_data[officer_name]:
                            if video['url'] == selected_video_url:
                                video['transcript'] = transcriptions
                                break
                        save_data(officer_data)
                        st.rerun()

with tabs[2]:
    st.subheader("Add a New Officer Video")
    st.caption("This tab lets you add a new body cam video by entering the officer’s name, video title, and YouTube URL, making it easy to expand the video database for review and analysis.")


    new_officer = st.text_input("Officer Name")
    new_video_title = st.text_input("Video Title")
    new_video_url = st.text_input("YouTube Video URL")

    if "video_added" not in st.session_state:
        st.session_state.video_added = False

    if st.button("Add Video"):
        if new_officer and new_video_url and new_video_title:
            new_entry = {
                "title": new_video_title,
                "url": new_video_url
            }
            officer_data = load_data()  # Reload in case of updates from other tab
            if new_officer in officer_data:
                officer_data[new_officer].append(new_entry)
            else:
                officer_data[new_officer] = [new_entry]
            save_data(officer_data)
            st.session_state.video_added = True
            st.rerun()
        else:
            st.error("Please fill out all fields before submitting.")

    # Show success message after rerun
    if st.session_state.get("video_added", False):
        st.success(f"Video added for Officer '{new_officer}'!")
        st.session_state.video_added = False
