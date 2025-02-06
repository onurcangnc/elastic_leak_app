import streamlit as st
import requests
from datetime import datetime

# Flask API URL (Elasticsearch'e bağlanan ara sunucu)
FLASK_API_URL = st.secrets["FLASK_API_URL"]

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

# -- Fonksiyon: Belirli sayfadaki sonuçları getir --
def fetch_results():
    if not query.strip():
        st.error("Lütfen bir arama sorgusu girin.")
        return

    try:
        response = requests.get(FLASK_API_URL, params={"q": query, "page": st.session_state.current_page})
        if response.status_code == 200:
            data = response.json()
            if "results" in data:
                st.session_state.all_results = data["results"]
                st.session_state.total_results = data["total_results"]
                st.session_state.page_size = data["page_size"]
                st.success(f"Toplam Sonuç: {st.session_state.total_results}")
            else:
                st.error("Beklenmeyen cevap formatı.")
        else:
            st.error(f"Hata: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Sonuçlar çekilirken hata oluştu: {e}")

# -- Arama Butonu --
if st.button("Search"):
    st.session_state.current_page = 1  # Yeni arama yapılırsa sayfayı sıfırla
    fetch_results()

# -- Sayfalama Kontrolleri --
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

# -- Mevcut Sayfadaki Sonuçları Göster --
if st.session_state.all_results:
    start_index = (st.session_state.current_page - 1) * st.session_state.page_size + 1
    for i, content in enumerate(st.session_state.all_results, start=start_index):
        st.text(f"{i}: {content}")

# -- Fonksiyon: Tüm Sonuçları Getir --
def fetch_all_results():
    all_results = []
    # Toplam sayfa sayısını hesapla
    total_pages = (st.session_state.total_results // st.session_state.page_size) + (1 if st.session_state.total_results % st.session_state.page_size != 0 else 0)
    for page in range(1, total_pages + 1):
        try:
            response = requests.get(FLASK_API_URL, params={"q": query, "page": page})
            if response.status_code == 200:
                data = response.json()
                if "results" in data:
                    all_results.extend(data["results"])
                else:
                    st.error(f"{page}. sayfada beklenmeyen cevap formatı.")
                    break
            else:
                st.error(f"{page}. sayfada hata: {response.status_code} - {response.text}")
                break
        except Exception as e:
            st.error(f"{page}. sayfada sonuç çekilirken hata oluştu: {e}")
            break
    return all_results

# -- Tüm Sonuçları İndirme Butonu --
if st.session_state.total_results > 0:
    if st.button("Download All Results"):
        full_results = fetch_all_results()
        if full_results:
            txt_content = "\n".join(full_results)
            st.download_button(
                label="Download Complete Results",
                data=txt_content,
                file_name=f"search_results_all_{datetime.now().strftime('%Y-%m-%d')}.txt",
                mime="text/plain"
            )
