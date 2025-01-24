
import streamlit as st
from elasticsearch import Elasticsearch

# Connect to Elasticsearch
es = Elasticsearch(
    "http://193.164.4.35:9200",
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

# Streamlit UI
st.title("Elasticsearch Leaks Viewer")

# Query input
query = st.text_input("Search Query (Use wildcard: *bilkent*):", "")
batch_size = 5000  # Number of results to fetch per batch
search_button = st.button("Search")
next_button = st.button("Load More Results")
download_button = st.button("Download All Results")

# Initialize session state
if "scroll_id" not in st.session_state:
    st.session_state.scroll_id = None
if "all_results" not in st.session_state:
    st.session_state.all_results = []
if "total_results" not in st.session_state:
    st.session_state.total_results = 0
if "current_batch" not in st.session_state:
    st.session_state.current_batch = []

# Function to fetch results from Elasticsearch
def fetch_results():
    try:
        if st.session_state.scroll_id is None:
            # Initial search query
            search_query = {
                "query": {
                    "wildcard": {
                        "content": {
                            "value": f"*{query}*",
                            "case_insensitive": True
                        }
                    }
                },
                "_source": ["content"],  # Fetch only 'content' field
                "size": batch_size
            }
            response = es.search(index="leaks", body=search_query, scroll="5m")
            st.session_state.scroll_id = response["_scroll_id"]
        else:
            # Fetch next batch using scroll
            response = es.scroll(scroll_id=st.session_state.scroll_id, scroll="5m")

        # Process hits
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

# Search and display results
if search_button:
    if not query.strip():
        st.error("Please enter a search query.")
    else:
        st.session_state.scroll_id = None  # Reset scroll ID for new query
        st.session_state.all_results = []  # Clear previous results
        st.session_state.total_results = 0  # Reset total result count
        fetch_results()
        if st.session_state.current_batch:
            st.success(f"Total Results Found: {st.session_state.total_results}")
            st.write("### Current Results:")
            for i, content in enumerate(st.session_state.current_batch, start=1):
                st.text(f"{i}: {content}")
        else:
            st.warning("No results found.")

# Load more results
if next_button and st.session_state.scroll_id:
    fetch_results()
    if st.session_state.current_batch:
        st.write("### More Results:")
        for i, content in enumerate(st.session_state.current_batch, start=st.session_state.total_results - len(st.session_state.current_batch) + 1):
            st.text(f"{i}: {content}")
    else:
        st.warning("No more results available.")

# Download all results
if download_button:
    if st.session_state.all_results:
        # Prepare text file content
        txt_content = "\n".join(st.session_state.all_results)
        st.download_button(
            label="Download Results as .txt",
            data=txt_content,
            file_name="search_results.txt",
            mime="text/plain"
        )
    else:
        st.warning("No results available for download.")
