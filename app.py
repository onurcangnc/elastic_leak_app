import streamlit as st
from elasticsearch import Elasticsearch
from datetime import datetime, timedelta

# Elasticsearch URL
ELASTICSEARCH_URL = st.secrets["ELASTICSEARCH_URL"]
USERNAME = st.secrets["ELASTICSEARCH_USER"]
PASSWORD = st.secrets["ELASTICSEARCH_PASSWORD"]

# Connect to Elasticsearch
es = Elasticsearch(
    [ELASTICSEARCH_URL],
    basic_auth=(USERNAME, PASSWORD),
    request_timeout=120,
    max_retries=10,
    retry_on_timeout=True
)

# Test connection
try:
    if not es.ping():
        st.error("Elasticsearch server is not reachable. Please check the server URL and network settings.")
        st.stop()
except Exception as e:
    st.error(f"Error connecting to Elasticsearch: {e}")
    st.stop()

st.title("Elasticsearch Leaks Viewer")

# -- Session State Defaults --
if "scroll_id" not in st.session_state:
    st.session_state.scroll_id = None
if "all_results" not in st.session_state:
    st.session_state.all_results = []
if "total_results" not in st.session_state:
    st.session_state.total_results = 0
if "current_page" not in st.session_state:
    st.session_state.current_page = 1

# -- Query Input --
query = st.text_input("Search Query (Exact Match):", "")
batch_size = 10000

index_names = "leaks-*"

# -- Fetch Results Function --
def fetch_results():
    try:
        st.session_state.scroll_id = None
        st.session_state.all_results = []
        st.session_state.total_results = 0
        
        while True:
            if st.session_state.scroll_id is None:
                # Initial search
                search_query = {
                    "query": {
                        "query_string": {
                            "query": f"*{query}*",  # wildcard
                            "default_field": "content",
                            "analyze_wildcard": True
                        }
                    },
                    "_source": ["content"],  # only fetch 'content'
                    "size": batch_size
                }
                response = es.search(index=index_names, body=search_query, scroll="5m")
                st.session_state.scroll_id = response["_scroll_id"]
            else:
                # Subsequent scroll calls
                response = es.scroll(scroll_id=st.session_state.scroll_id, scroll="5m")
            
            hits = response["hits"]["hits"]
            if not hits:
                st.session_state.scroll_id = None
                break
            
            # Collect results
            batch = [hit["_source"]["content"] for hit in hits]
            st.session_state.all_results.extend(batch)
            st.session_state.total_results += len(batch)

            # Show real-time progress
            st.write(f"Fetched {st.session_state.total_results} results so far...")
    
    except Exception as e:
        st.error(f"Error during fetching results: {e}")
        st.session_state.scroll_id = None

# -- Pagination Function --
PAGE_SIZE = 100

def display_paginated_results():
    total_pages = (
        st.session_state.total_results // PAGE_SIZE
        + (1 if st.session_state.total_results % PAGE_SIZE != 0 else 0)
    )
    current_page = st.session_state.current_page

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        if st.button("Previous", key="prev_btn") and current_page > 1:
            st.session_state.current_page -= 1
    with col3:
        if st.button("Next", key="next_btn") and current_page < total_pages:
            st.session_state.current_page += 1

    current_page = st.session_state.current_page
    start_idx = (current_page - 1) * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE

    st.write(f"Showing page {current_page} of {total_pages}")
    page_results = st.session_state.all_results[start_idx:end_idx]
    for i, content in enumerate(page_results, start=start_idx + 1):
        st.text(f"{i}: {content}")

# -- Search Button --
search_button = st.button("Search")

# -- Handle Search Click --
if search_button:
    if not query.strip():
        st.error("Please enter a search query.")
    else:
        # Reset page to 1 on new search
        st.session_state.current_page = 1
        
        status_placeholder = st.empty()
        status_placeholder.info("Fetching in progress... Please wait...")

        fetch_results()

        if st.session_state.all_results:
            status_placeholder.success(
                f"All results fetched successfully! Total Results Found: {st.session_state.total_results}"
            )
        else:
            status_placeholder.error("No results found.")

# -- Download Button (Immediately Below Search Button) --
#   Only show if there are results
if st.session_state.all_results:
    txt_content = "\n".join(st.session_state.all_results)
    st.download_button(
        label="Download All Results",
        data=txt_content,
        file_name=f"search_results_{datetime.now().strftime('%Y-%m-%d')}.txt",
        mime="text/plain"
    )

# -- Pagination (if results exist) --
if st.session_state.all_results:
    display_paginated_results()
