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
query = st.text_input("Search Query (Use wildcard: *bilkent*):", "")
batch_size = 5000  # Kaç sonuç çekileceği
search_button = st.button("Search")
next_button = st.button("Load More Results")
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

# Elasticsearch'teki bugünkü indeks adını hesaplama
today_date = datetime.now().strftime("%Y-%m-%d")
index_name = f"leaks-{today_date}"

# Sonuçları Elasticsearch'ten çekmek için fonksiyon
def fetch_results():
    try:
        if st.session_state.scroll_id is None:
            # Case-insensitive exact match query
            search_query = {
                "query": {
                    "match": {
                        "content": {
                            "query": query,
                            "operator": "and",
                            "fuzziness": "0",  # Ensures exact match
                        }
                    }
                },
                "_source": ["content"],  # Only fetch the 'content' field
                "size": batch_size
            }
            response = es.search(index=index_name, body=search_query, scroll="5m")
            st.session_state.scroll_id = response["_scroll_id"]
        else:
            # Scroll ID for fetching the next batch
            response = es.scroll(scroll_id=st.session_state.scroll_id, scroll="5m")

        # Process the results
        hits = response["hits"]["hits"]
        if hits:
            batch = [hit["_source"]["content"] for hit in hits]
            st.session_state.current_batch = batch
            st.session_state.all_results.extend(batch)
            st.session_state.total_results += len(batch)
        else:
            st.session_state.current_batch = []
            st.session_state.scroll_id = None  # Clear scroll ID if no more results
    except Exception as e:
        st.error(f"Error during fetching results: {e}")
        st.session_state.scroll_id = None

# Arama ve sonuçları görüntüleme
if search_button:
    if not query.strip():
        st.error("Please enter a search query.")
    else:
        st.session_state.scroll_id = None  # Yeni sorgu için scroll ID sıfırla
        st.session_state.all_results = []  # Önceki sonuçları temizle
        st.session_state.total_results = 0  # Toplam sonucu sıfırla
        fetch_results()
        if st.session_state.current_batch:
            st.success(f"Total Results Found: {st.session_state.total_results}")
            st.write("### Current Results:")
            for i, content in enumerate(st.session_state.current_batch, start=1):
                st.text(f"{i}: {content}")
        else:
            st.warning("No results found.")

# Daha fazla sonuç yükleme
if next_button and st.session_state.scroll_id:
    fetch_results()
    if st.session_state.current_batch:
        st.write("### More Results:")
        for i, content in enumerate(st.session_state.current_batch, start=st.session_state.total_results - len(st.session_state.current_batch) + 1):
            st.text(f"{i}: {content}")
    else:
        st.warning("No more results available.")

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
