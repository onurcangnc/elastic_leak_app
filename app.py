import streamlit as st
import requests
import math

FLASK_API_URL = "http://localhost:5000/search"  # Örnek

# State başlangıç
if "all_results" not in st.session_state:
    st.session_state.all_results = []
if "current_page" not in st.session_state:
    st.session_state.current_page = 1
if "total_results" not in st.session_state:
    st.session_state.total_results = 0
if "page_size" not in st.session_state:
    st.session_state.page_size = 100
if "data_fetched" not in st.session_state:
    st.session_state.data_fetched = False

def fetch_page(query, page_number, page_size=100):
    """ Örnek sayfa çekme fonksiyonu (size, offset mantığı).
        Arka planda Flask API'niz de search_after kullanabilir.
    """
    params = {
        "q": query,
        "page_size": page_size,
        "page_number": page_number
    }
    r = requests.get(FLASK_API_URL, params=params)
    r.raise_for_status()
    return r.json()  # Expected: {"results": [...], "total_results": N}

def fetch_all_pages(query):
    """ Tüm sayfaları (sonuna kadar) otomatik çek. """
    first_page_data = fetch_page(query, 1, st.session_state.page_size)
    st.session_state.all_results.extend(first_page_data["results"])
    st.session_state.total_results = first_page_data["total_results"]

    total_pages = math.ceil(first_page_data["total_results"] / st.session_state.page_size)

    # Kalan sayfaları ardışık çek
    for p in range(2, total_pages + 1):
        next_page_data = fetch_page(query, p, st.session_state.page_size)
        st.session_state.all_results.extend(next_page_data["results"])
        # Burada isterseniz st.experimental_rerun() ile ekrana anlık yansıtabilirsiniz

st.title("Auto-Fetch Paginated Results")

query = st.text_input("Search Query:", "")

if st.button("Search"):
    st.session_state.all_results = []
    st.session_state.current_page = 1
    st.session_state.total_results = 0
    st.session_state.data_fetched = False

    if query.strip():
        try:
            fetch_all_pages(query)
            st.session_state.data_fetched = True
        except Exception as e:
            st.error(f"Error: {e}")

# Eğer veriler çekildiyse, sayfalama göster
if st.session_state.data_fetched and st.session_state.total_results > 0:
    total_pages = math.ceil(st.session_state.total_results / st.session_state.page_size)
    
    # Butonlar
    col1, col2 = st.columns([1,1])
    with col1:
        if st.button("Previous") and st.session_state.current_page > 1:
            st.session_state.current_page -= 1
    with col2:
        if st.button("Next") and st.session_state.current_page < total_pages:
            st.session_state.current_page += 1

    st.write(f"Showing page {st.session_state.current_page} of {total_pages}")

    start_idx = (st.session_state.current_page - 1) * st.session_state.page_size
    end_idx = start_idx + st.session_state.page_size
    page_data = st.session_state.all_results[start_idx:end_idx]

    for i, content in enumerate(page_data, start=start_idx+1):
        st.write(f"{i}: {content}")

    # İndirme
    if st.session_state.all_results:
        txt_content = "\n".join(st.session_state.all_results)
        st.download_button("Download All Results", data=txt_content, file_name=f"{query}.txt")

