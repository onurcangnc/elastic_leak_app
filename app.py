import streamlit as st
import requests

FLASK_API_URL = st.secrets["FLASK_API_URL"]

st.title("Elasticsearch Leaks Viewer")

# ✅ İlk başta session state içeriği sıfır olsun
if "all_results" not in st.session_state:
    st.session_state.all_results = []
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "total_results" not in st.session_state:
    st.session_state.total_results = 0
if "page_size" not in st.session_state:
    st.session_state.page_size = 100

query = st.text_input("Search Query (Exact Match):", "")

def fetch_results():
    """Elasticsearch'ten veriyi getirip bellekte saklayan fonksiyon"""
    if not query.strip():
        st.error("Please enter a search query.")
        return

    params = {"q": query}
    
    try:
        response = requests.get(FLASK_API_URL, params=params)
        if response.status_code == 200:
            data = response.json()

            if "results" in data:
                st.session_state.all_results = data["results"]  # ✅ Tüm veriyi belleğe kaydet
                st.session_state.total_results = data["total_results"]
                st.session_state.page_size = data.get("page_size", 100)
                st.session_state.current_page = 1  # ✅ Sayfa sıfırlansın
                st.success(f"Total Results Found: {st.session_state.total_results}")
            else:
                st.error("Unexpected response format.")
        else:
            st.error(f"Error: {response.status_code} - {response.text}")

    except Exception as e:
        st.error(f"Error fetching results: {e}")

if st.button("Search"):
    st.session_state.all_results = []  # ✅ Yeni arama yapıldığında sonuçları sıfırla
    fetch_results()

# ✅ Sayfalama için toplam sayfa hesapla
total_pages = (len(st.session_state.all_results) // st.session_state.page_size) + (
    1 if len(st.session_state.all_results) % st.session_state.page_size != 0 else 0
)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Previous") and st.session_state.current_page > 1:
        st.session_state.current_page -= 1
with col2:
    if st.button("Next") and st.session_state.current_page < total_pages:
        st.session_state.current_page += 1

st.write(f"Showing page {st.session_state.current_page} of {total_pages}")

# ✅ Şu anki sayfadaki verileri göster
start_idx = (st.session_state.current_page - 1) * st.session_state.page_size
end_idx = start_idx + st.session_state.page_size
page_data = st.session_state.all_results[start_idx:end_idx]

if page_data:
    for i, content in enumerate(page_data, start=start_idx + 1):
        st.text(f"{i}: {content}")

# ✅ Tüm sonuçları indir
if st.session_state.all_results:
    txt_content = "\n".join(st.session_state.all_results)
    st.download_button(
        label="Download All Results",
        data=txt_content,
        file_name=f"search_results.txt",
        mime="text/plain"
    )
