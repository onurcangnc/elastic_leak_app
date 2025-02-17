import streamlit as st
import requests
import threading
import time
from datetime import datetime

# Flask API URL (Elasticsearch'e bağlanan ara sunucu)
FLASK_API_URL = st.secrets["FLASK_API_URL"]

# Streamlit Keep-Alive URL (Kendi Uygulamanın URL'sini Buraya Yaz)
STREAMLIT_APP_URL = st.secrets["STREAMLIT_APP_URL"]

# ✅ Keep-Alive Fonksiyonu (Streamlit Uygulamasına Kendisi Ping Atar)
def keep_alive():
    while True:
        try:
            response = requests.get(STREAMLIT_APP_URL)
            if response.status_code == 200:
                print("✅ Keep-Alive başarılı! Streamlit uygulaması aktif.")
            else:
                print(f"⚠️ Keep-Alive hatası: {response.status_code}")
        except Exception as e:
            print(f"🚨 Bağlantı hatası: {e}")
        
        time.sleep(300)  # 5 dakikada bir ping at

# ✅ Streamlit başlatılırken Keep-Alive Thread başlat
if "keep_alive_thread" not in st.session_state:
    keep_alive_thread = threading.Thread(target=keep_alive, daemon=True)
    keep_alive_thread.start()
    st.session_state["keep_alive_thread"] = True

st.title("Elasticsearch Leaks Viewer")

# -- Session State Defaults --
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "all_results" not in st.session_state:
    st.session_state.all_results = []
if "total_results" not in st.session_state:
    st.session_state.total_results = 0
if "page_size" not in st.session_state:
    st.session_state.page_size = 100

# -- Query Input --
query = st.text_input("Search Query (Exact Match):", "")

# -- Fetch Results Function --
def fetch_results():
    if not query.strip():
        st.error("Please enter a search query.")
        return

    try:
        response = requests.get(FLASK_API_URL, params={"q": query, "page": st.session_state.current_page})
        if response.status_code == 200:
            data = response.json()
            if "results" in data:
                st.session_state.all_results = data["results"]
                st.session_state.total_results = data["total_results"]
                st.session_state.page_size = data["page_size"]
                st.success(f"Total Results Found: {st.session_state.total_results}")
            else:
                st.error("Unexpected response format.")
        else:
            st.error(f"Error: {response.status_code} - {response.text}")

    except Exception as e:
        st.error(f"Error fetching results: {e}")

# -- Search Button --
if st.button("Search"):
    st.session_state.current_page = 1  # Yeni arama yapıldığında sayfa sıfırlansın
    fetch_results()

# -- Pagination Controls --
total_pages = (st.session_state.total_results // st.session_state.page_size) + (1 if st.session_state.total_results % st.session_state.page_size != 0 else 0)

col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("Previous") and st.session_state.current_page > 1:
        st.session_state.current_page -= 1
        fetch_results()
with col3:
    if st.button("Next") and st.session_state.current_page < total_pages:
        st.session_state.current_page += 1
        fetch_results()

st.write(f"Showing page {st.session_state.current_page} of {total_pages}")

# -- Display Results --
if st.session_state.all_results:
    for i, content in enumerate(st.session_state.all_results, start=(st.session_state.current_page - 1) * st.session_state.page_size + 1):
        st.text(f"{i}: {content}")

# -- Download Button --
if st.session_state.all_results:
    txt_content = "\n".join(st.session_state.all_results)
    st.download_button(
        label="Download All Results",
        data=txt_content,
        file_name=f"search_results_{datetime.now().strftime('%Y-%m-%d')}.txt",
        mime="text/plain"
    )
