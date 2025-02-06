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

def fetch_all_pages(query: str):
    """
    Belirtilen query için API'den tüm sayfaları çekip döndürür.
    Return:
        all_results (list): Toplam tüm sayfalardaki sonuçların listesi.
        total_results (int): Toplam sonuç sayısı.
        page_size (int): Bir sayfadaki sonuç adedi.
    """
    try:
        # 1) İlk sayfayı çek
        page = 1
        response = requests.get(FLASK_API_URL, params={"q": query, "page": page})
        if response.status_code != 200:
            st.error(f"Error: {response.status_code} - {response.text}")
            return [], 0, 100

        data = response.json()
        if "results" not in data:
            st.error("Unexpected response format.")
            return [], 0, 100

        # İlk sayfa sonuçlarını al
        all_results = data["results"]
        total_results = data["total_results"]
        page_size = data["page_size"]

        # Toplam sayfa sayısını hesapla
        total_pages = (total_results // page_size) + (1 if total_results % page_size != 0 else 0)

        # 2) Kalan sayfaları döngüyle çek
        for p in range(2, total_pages + 1):
            resp = requests.get(FLASK_API_URL, params={"q": query, "page": p})
            if resp.status_code != 200:
                st.error(f"Error on page {p}: {resp.status_code} - {resp.text}")
                break
            d = resp.json()
            if "results" not in d:
                st.error(f"Unexpected response format on page {p}.")
                break
            all_results.extend(d["results"])

        return all_results, total_results, page_size

    except Exception as e:
        st.error(f"Error fetching all results: {e}")
        return [], 0, 100

# -- Search Button --
if st.button("Search"):
    # Yeni arama yapıldığında sayfa sıfırlansın
    st.session_state.current_page = 1

    # Tüm sayfaları tek seferde toplayalım
    if not query.strip():
        st.error("Please enter a search query.")
    else:
        all_results, total_results, page_size = fetch_all_pages(query)
        st.session_state.all_results = all_results
        st.session_state.total_results = total_results
        st.session_state.page_size = page_size

        st.success(f"Toplam Sonuç: {total_results}")

# -- Toplam sayfa sayısı (lokal bellekten hesaplıyoruz) --
total_pages = 0
if st.session_state.total_results > 0 and st.session_state.page_size > 0:
    total_pages = (st.session_state.total_results // st.session_state.page_size) + (
        1 if st.session_state.total_results % st.session_state.page_size != 0 else 0
    )

# -- Pagination Controls --
col1, col2, col3 = st.columns([1, 1, 1])
with col1:
    if st.button("Previous") and st.session_state.current_page > 1:
        st.session_state.current_page -= 1
with col3:
    if st.button("Next") and st.session_state.current_page < total_pages:
        st.session_state.current_page += 1

st.write(f"Showing page {st.session_state.current_page} of {total_pages if total_pages else 1}")

# -- Display Results (yalnızca ilgili sayfadaki slice gösterilir) --
if st.session_state.all_results:
    start_idx = (st.session_state.current_page - 1) * st.session_state.page_size
    end_idx = start_idx + st.session_state.page_size
    page_results = st.session_state.all_results[start_idx:end_idx]

    for i, content in enumerate(page_results, start=start_idx + 1):
        st.text(f"{i}: {content}")

# -- Download Button (Tüm sonuçlar) --
if st.session_state.all_results:
    txt_content = "\n".join(st.session_state.all_results)
    st.download_button(
        label="Download All Results",
        data=txt_content,
        file_name=f"search_results_{datetime.now().strftime('%Y-%m-%d')}.txt",
        mime="text/plain"
    )
