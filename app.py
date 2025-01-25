import streamlit as st
from elasticsearch import Elasticsearch
from datetime import datetime

# Elasticsearch URL'sini Streamlit Secrets'ten al
ELASTICSEARCH_URL = st.secrets["ELASTICSEARCH_URL"]

# Elasticsearch'e bağlan
es = Elasticsearch(
    ELASTICSEARCH_URL,
    request_timeout=120,
    max_retries=10,
    retry_on_timeout=True
)

# Elasticsearch bağlantısını test et
try:
    if not es.ping():
        st.error("Elasticsearch server is not reachable. Please check the server URL and network settings.")
        st.stop()
except Exception as e:
    st.error(f"Error connecting to Elasticsearch: {e}")
    st.stop()

# Streamlit UI
st.title("Elasticsearch Leaks Viewer")

# Sorgu girişi
query = st.text_input("Search Query (Exact Match):", "")
batch_size = 5000  # Scroll API ile her seferinde çekilecek sonuç sayısı
search_button = st.button("Search")
download_button = st.button("Download All Results")

# Session State ile kontrol
if "scroll_id" not in st.session_state:
    st.session_state.scroll_id = None
if "all_results" not in st.session_state:
    st.session_state.all_results = []
if "total_results" not in st.session_state:
    st.session_state.total_results = 0
if "current_batch" not in st.session_state:
    st.session_state.current_batch = []
if "search_in_progress" not in st.session_state:
    st.session_state.search_in_progress = False

# Elasticsearch'teki bugünkü indeks adını hesaplama
today_date = datetime.now().strftime("%Y-%m-%d")
index_name = f"leaks-{today_date}"

# Sonuçları Elasticsearch'ten çekmek için fonksiyon
def fetch_results():
    try:
        st.session_state.search_in_progress = True  # Arama başladı
        while True:
            if st.session_state.scroll_id is None:
                # İlk sorgu
                search_query = {
                    "query": {
                        "query_string": {
                            "query": f"*{query}*",  # wildcard destekli sorgu
                            "default_field": "content",
                            "analyze_wildcard": True
                        }
                    },
                    "_source": ["content"],  # Sadece 'content' alanı çekiliyor
                    "size": batch_size
                }
                response = es.search(index=index_name, body=search_query, scroll="5m")
                st.session_state.scroll_id = response["_scroll_id"]
            else:
                # Scroll ID ile sonraki batch çekiliyor
                response = es.scroll(scroll_id=st.session_state.scroll_id, scroll="5m")

            # Gelen sonuçları işleme
            hits = response["hits"]["hits"]
            if not hits:
                st.session_state.scroll_id = None  # Sonuç kalmadıysa scroll ID temizle
                break

            # Sonuçları toplama
            batch = [hit["_source"]["content"] for hit in hits]
            st.session_state.current_batch = batch
            st.session_state.all_results.extend(batch)
            st.session_state.total_results += len(batch)

            # Gerçek zamanlı olarak sonuçları ekrana yazdırma
            st.write(f"Fetched {st.session_state.total_results} results so far...")
            with st.expander("Real-Time Results", expanded=True):
                for i, content in enumerate(batch, start=st.session_state.total_results - len(batch) + 1):
                    st.text(f"{i}: {content}")

    except Exception as e:
        st.error(f"Error during fetching results: {e}")
        st.session_state.scroll_id = None
    finally:
        st.session_state.search_in_progress = False  # Arama tamamlandı

# Durum göstergesi için ayrı bir alan
status_placeholder = st.empty()

# Arama başlatıldığında
if search_button:
    if not query.strip():
        st.error("Please enter a search query.")
    else:
        # Önceki sonuçları temizle
        st.session_state.scroll_id = None
        st.session_state.all_results = []
        st.session_state.total_results = 0

        # Durum kutusu: Kırmızı (Fetching)
        status_placeholder.error("Fetching in progress... Please wait.")

        fetch_results()

        # Durum kutusu: Yeşil (All results fetched)
        if st.session_state.all_results:
            status_placeholder.success(f"All results fetched successfully! Total Results Found: {st.session_state.total_results}")
            st.write("### Final Results:")
            with st.expander("All Results", expanded=True):
                for i, content in enumerate(st.session_state.all_results, start=1):
                    st.text(f"{i}: {content}")
        else:
            status_placeholder.error("No results found.")

# Tüm sonuçları indirme
if download_button:
    if st.session_state.all_results:
        # Text dosyasını hazırla
        txt_content = "\n".join(st.session_state.all_results)
        st.download_button(
            label="Download Results as .txt",
            data=txt_content,
            file_name=f"search_results_{today_date}.txt",
            mime="text/plain"
        )
    else:
        st.warning("No results available for download.")
