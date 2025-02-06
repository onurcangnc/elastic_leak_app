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

# -- Standart Sayfalı Sonuçları Çekmek İçin Fonksiyon --
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
                st.success(f"Toplam Sonuç Sayısı: {st.session_state.total_results}")
            else:
                st.error("Beklenmeyen cevap formatı.")
        else:
            st.error(f"Hata: {response.status_code} - {response.text}")
    except Exception as e:
        st.error(f"Sonuçlar çekilirken hata oluştu: {e}")

# -- Arama Butonu --
if st.button("Search"):
    st.session_state.current_page = 1  # Yeni arama yapıldığında sayfa sıfırlansın
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

# -- Standart Sayfadaki Sonuçların Gösterimi --
if st.session_state.all_results:
    start_index = (st.session_state.current_page - 1) * st.session_state.page_size + 1
    for i, content in enumerate(st.session_state.all_results, start=start_index):
        st.text(f"{i}: {content}")

# -- Scroll API Kullanarak Tüm Sonuçları Çekmek İçin Fonksiyon --
def fetch_all_results_scroll():
    all_results = []
    try:
        # Scroll oturumunu başlatmak için ilk istek
        response = requests.get(FLASK_API_URL, params={"q": query, "scroll": "true"})
        if response.status_code != 200:
            st.error(f"Scroll başlatılırken hata: {response.status_code} - {response.text}")
            return all_results
        
        data = response.json()
        results = data.get("results", [])
        all_results.extend(results)
        scroll_id = data.get("scroll_id")
        
        # Scroll ile kalan sonuçları çekmek için döngü
        while True:
            # scroll_id parametresi ile sonraki veri parçasını çekiyoruz
            response = requests.get(FLASK_API_URL, params={"scroll_id": scroll_id, "scroll": "true"})
            if response.status_code != 200:
                st.error(f"Scroll devam ederken hata: {response.status_code} - {response.text}")
                break
            data = response.json()
            results = data.get("results", [])
            if not results:
                break  # Sonuç kalmadıysa döngüden çık
            all_results.extend(results)
            scroll_id = data.get("scroll_id")
        return all_results
    except Exception as e:
        st.error(f"Scroll sonuçları çekilirken hata oluştu: {e}")
        return all_results

# -- Scroll API Tabanlı Tüm Sonuçları İndirme Butonu --
if st.session_state.total_results > 0:
    if st.button("Download All Results (Scroll API)"):
        full_results = fetch_all_results_scroll()
        if full_results:
            txt_content = "\n".join(full_results)
            st.download_button(
                label="Download Complete Results",
                data=txt_content,
                file_name=f"search_results_all_{datetime.now().strftime('%Y-%m-%d')}.txt",
                mime="text/plain"
            )
