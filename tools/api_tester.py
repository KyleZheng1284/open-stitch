"""Open-Stitch MVP — user flow tester.

Real user flow:
  1. Upload videos (auto-creates project, starts ingestion immediately)
  2. Describe style/vibe → clarifying agent → orchestrator → edit pipeline
  3. Monitor pipeline progress
  4. Review rendered clips & publish

Run:  streamlit run tools/api_tester.py
Needs: backend on http://localhost:8080
"""
from uuid import uuid4

import requests
import streamlit as st

st.set_page_config(page_title="Open-Stitch", layout="wide")

BASE = "http://localhost:8080"

# ── Auto-generate session ID on first load ──
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid4())[:8]
if "project_id" not in st.session_state:
    st.session_state.project_id = None
if "videos" not in st.session_state:
    st.session_state.videos = []
if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "ingestion_started" not in st.session_state:
    st.session_state.ingestion_started = False


def api(method: str, path: str, **kwargs) -> dict | None:
    try:
        r = getattr(requests, method)(f"{BASE}{path}", timeout=30, **kwargs)
        if r.ok:
            return r.json()
        else:
            st.error(f"Error {r.status_code}: {r.text}")
            return None
    except requests.ConnectionError:
        st.error("Backend not running — `uvicorn autovid.api.app:app --port 8080 --reload`")
        return None


def ensure_project() -> str:
    """Create project on first upload if it doesn't exist yet."""
    if st.session_state.project_id:
        return st.session_state.project_id
    data = api("post", "/api/v1/projects", json={
        "video_uris": [],
        "style_prompt": "",
    })
    if data:
        st.session_state.project_id = data["project_id"]
        return data["project_id"]
    return ""


# ── Sidebar ──
st.sidebar.title("Open-Stitch")

# Connection
try:
    requests.get(f"{BASE}/health", timeout=2)
    st.sidebar.success("Backend connected")
except requests.ConnectionError:
    st.sidebar.error("Backend offline")

st.sidebar.divider()
st.sidebar.caption(f"Session `{st.session_state.session_id}`")
if st.session_state.project_id:
    st.sidebar.code(f"Project: {st.session_state.project_id[:8]}...")
if st.session_state.videos:
    st.sidebar.write(f"{len(st.session_state.videos)} video(s)")
if st.session_state.ingestion_started:
    st.sidebar.write("Ingestion: running")
if st.session_state.job_id:
    st.sidebar.code(f"Job: {st.session_state.job_id[:8]}...")

if st.sidebar.button("New Session"):
    st.session_state.clear()
    st.rerun()


# ── Main ──
st.title("Open-Stitch")

tab1, tab2, tab3, tab4 = st.tabs([
    "1. Upload",
    "2. Style & Edit",
    "3. Pipeline",
    "4. Review & Publish",
])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 1: Upload — this is the landing experience
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab1:
    st.subheader("Drop your raw footage")
    st.caption("Upload first — ingestion (chunking, ASR, VLM analysis) starts automatically per video.")

    uploaded_files = st.file_uploader(
        "Video files",
        type=["mp4", "mov", "avi", "mkv"],
        accept_multiple_files=True,
        key="upload_files",
    )

    if st.button("Upload & Start Ingestion", type="primary", key="btn_upload") and uploaded_files:
        project_id = ensure_project()
        if project_id:
            for f in uploaded_files:
                with st.spinner(f"Uploading {f.name}..."):
                    data = api(
                        "post",
                        f"/api/v1/projects/{project_id}/upload",
                        files={"file": (f.name, f, f.type or "video/mp4")},
                    )
                    if data:
                        st.session_state.videos.append(data)
                        st.session_state.ingestion_started = True
                        st.success(f"{f.name} uploaded — ingestion queued")

    # Show uploaded videos
    if st.session_state.videos:
        st.divider()
        st.write("**Uploaded & ingesting:**")
        for i, v in enumerate(st.session_state.videos):
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.write(f"**{v.get('filename', 'unknown')}**")
            col2.code(v["video_id"][:12] + "...")
            col3.caption(v.get("status", ""))

        if st.button("Check Ingestion Status", key="btn_ingest_status"):
            data = api("get", f"/api/v1/projects/{st.session_state.project_id}")
            if data:
                st.json(data)

        st.info("Videos are being ingested in the background. You can move to Tab 2 to set your style while ingestion runs.")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 2: Style & edit — describe what you want
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab2:
    st.subheader("Describe your edit")

    if not st.session_state.videos:
        st.warning("Upload at least one video first — but you can start describing your style now.")

    st.caption(
        "Your prompt goes through: clarifying agent → orchestrator → planner → "
        "ReAct loop → subtitle/music/meme agents → assembly"
    )

    edit_prompt = st.text_area(
        "What vibe are you going for?",
        placeholder="e.g. fast-paced TikTok energy, meme overlays on the funny moments, "
                    "bass-boosted transitions, karaoke-style subtitles, dark humor captions",
        height=120,
        key="edit_style",
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        platform = st.selectbox("Platform", ["youtube_shorts", "tiktok", "instagram_reels"])
        clip_count = st.slider("Clips to generate", 1, 10, 3)
    with col2:
        subtitle_style = st.selectbox("Subtitles", ["tiktok_pop", "minimal", "karaoke", "outline"])
        include_memes = st.checkbox("Meme overlays", value=True)
    with col3:
        include_music = st.checkbox("Background music", value=True)
        include_sfx = st.checkbox("Sound effects", value=True)

    can_edit = bool(st.session_state.project_id and st.session_state.videos)

    if st.button(
        "Start Editing" if can_edit else "Upload videos first",
        type="primary",
        disabled=not can_edit,
        key="btn_edit",
    ):
        data = api(
            "post",
            f"/api/v1/projects/{st.session_state.project_id}/edit",
            params={"style_prompt": edit_prompt or "default edit"},
        )
        if data:
            st.session_state.job_id = data["job_id"]
            st.success(f"Pipeline started — job `{data['job_id'][:8]}...`")
            st.json(data)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 3: Pipeline monitor
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab3:
    st.subheader("Pipeline progress")

    if not st.session_state.job_id:
        st.warning("No active job — start an edit in Tab 2")
    else:
        st.caption(f"Job `{st.session_state.job_id}`")

        if st.button("Refresh", type="primary", key="btn_refresh"):
            data = api("get", f"/api/v1/jobs/{st.session_state.job_id}")
            if data:
                progress = data.get("progress", 0.0)
                st.progress(progress, text=f"{progress*100:.0f}%")

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Status", data.get("status", "unknown"))
                col2.metric("Phase", data.get("phase", "-"))
                col3.metric("Step", data.get("step", "-"))
                col4.metric("ReAct #", data.get("react_iteration", 0))

                with st.expander("Raw response"):
                    st.json(data)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TAB 4: Review & publish
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
with tab4:
    st.subheader("Review & publish")

    clip_id = st.text_input("Clip ID", placeholder="paste from pipeline output", key="clip_id")

    if clip_id:
        col_left, col_right = st.columns([2, 1])

        with col_left:
            if st.button("Load Clip", key="btn_load"):
                data = api("get", f"/api/v1/clips/{clip_id}")
                if data:
                    st.session_state["loaded_clip"] = data

            if "loaded_clip" in st.session_state:
                clip = st.session_state["loaded_clip"]
                m1, m2 = st.columns(2)
                m1.metric("Status", clip.get("status", "unknown"))
                m2.metric("Duration", f"{clip.get('duration_ms', 0) / 1000:.1f}s")

                if clip.get("download_url"):
                    st.video(clip["download_url"])
                else:
                    st.info("No rendered video yet")

                with st.expander("Clip metadata"):
                    st.json(clip)

        with col_right:
            st.write("**Publish to:**")
            pub_platforms = st.multiselect(
                "Platforms",
                ["youtube_shorts", "tiktok", "instagram_reels"],
                key="pub_plat",
            )
            if st.button("Publish", type="primary", key="btn_pub") and pub_platforms:
                data = api("post", f"/api/v1/clips/{clip_id}/publish", json=pub_platforms)
                if data:
                    st.success("Publishing started")
                    st.json(data)
