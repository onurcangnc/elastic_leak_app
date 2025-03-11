import streamlit as st
import requests
import math

FLASK_API_URL = st.secrets["FLASK_API_URL"]  # Örnek

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
if "fetch_index" not in st.session_state:
    st.session_state.fetch_index = 1  # Kaçıncı sayfayı çekiyoruz

def fetch_page(query, page_number, page_size=100):
    """
    Örnek sayfa çekme fonksiyonu (size, offset).
    Arka planda Flask API'nizde search_after kullanıyor da olabilirsiniz.
    Yanıt: {"results": [...], "total_results": N}
    """
    params = {
        "q": query,
        "page_size": page_size,
        "page_number": page_number
    }
    r = requests.get(FLASK_API_URL, params=params)
    r.raise_for_status()
    return r.json()

def fetch_all_pages_kademeli(query):
    """
    Tüm sayfaları sırayla, her part geldikçe ekrana yansıtacak şekilde
    kademeli veri çekme fonksiyonu.
    """
    # Eğer ilk sayfa henüz çekilmediyse (fetch_index = 1) ilk sayfa çek
    if st.session_state.fetch_index == 1:
        first_page_data = fetch_page(query, 1, st.session_state.page_size)
        st.session_state.all_results.extend(first_page_data["results"])
        st.session_state.total_results = first_page_data["total_results"]
        total_pages = math.ceil(first_page_data["total_results"] / st.session_state.page_size)
        # total_pages'ı kaydediyoruz ki sonraki rerun'larda tekrar hesaplamayalım
        st.session_state.total_pages = total_pages
        st.session_state.fetch_index = 2  # Bir sonraki sayfa
        st.rerun()  # UI’ı güncelle, veriler anlık görünsün

    # Eğer ilk sayfa çekildiyse, kalan sayfaları sırayla çekelim
    total_pages = st.session_state.total_pages
    while st.session_state.fetch_index <= total_pages:
        next_page_data = fetch_page(query, st.session_state.fetch_index, st.session_state.page_size)
        st.session_state.all_results.extend(next_page_data["results"])
        st.session_state.fetch_index += 1
        st.rerun()  # Her part çekişte UI’ı tekrar yenile

    # Tüm sayfalar bitti
    st.session_state.data_fetched = True
    st.rerun()

st.title("Elastic Leak Searcher (Kademeli)")

query = st.text_input("Search Query:", "")

if st.button("Search"):
    # Arama butonuna basıldığında her şeyi sıfırla
    st.session_state.all_results = []
    st.session_state.current_page = 1
    st.session_state.total_results = 0
    st.session_state.data_fetched = False
    st.session_state.fetch_index = 1  # En baştan başlayacağız

    if query.strip():
        try:
            fetch_all_pages_kademeli(query)
        except Exception as e:
            st.error(f"Error: {e}")

# Eğer veriler çekildiyse, sayfalama göster
if st.session_state.data_fetched and st.session_state.total_results > 0:
    total_pages = math.ceil(st.session_state.total_results / st.session_state.page_size)
    
    # Sayfalama butonları
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

    # Göster
    for i, content in enumerate(page_data, start=start_idx+1):
        st.write(f"{i}: {content}")

    # Tüm sonuçları indir
    if st.session_state.all_results:
        txt_content = "\n".join(st.session_state.all_results)
        st.download_button("Download All Results", data=txt_content, file_name=f"{query}.txt")
