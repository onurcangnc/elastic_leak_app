import streamlit as st
import requests
from datetime import datetime

# Flask API URL (Elasticsearch'e bağlanan ara sunucu)
FLASK_API_URL = st.secrets["ELASTICSEARCH_URL"]

st.title("Elasticsearch Leaks Viewer")

# -- Query Input --
query = st.text_input("Search Query (Exact Match):", "")

# -- Fetch Results Function --
def fetch_results():
    if not query.strip():
        st.error("Please enter a search query.")
        return

    try:
        response = requests.get(FLASK_API_URL, params={"q": query})
        if response.status_code == 200:
            data = response.json()
            if "hits" in data and "hits" in data["hits"]:
                results = [hit["_source"]["content"] for hit in data["hits"]["hits"]]
                if results:
                    st.session_state["all_results"] = results
                    st.session_state["total_results"] = len(results)
                    st.success(f"Total Results Found: {len(results)}")
                else:
                    st.error("No results found.")
            else:
                st.error("Unexpected response format.")
        else:
            st.error(f"Error: {response.status_code} - {response.text}")

    except Exception as e:
        st.error(f"Error fetching results: {e}")

# -- Search Button --
if st.button("Search"):
    fetch_results()

# -- Download Button --
if "all_results" in st.session_state and st.session_state["all_results"]:
    txt_content = "\n".join(st.session_state["all_results"])
    st.download_button(
        label="Download All Results",
        data=txt_content,
        file_name=f"search_results_{datetime.now().strftime('%Y-%m-%d')}.txt",
        mime="text/plain"
    )

# -- Display Results --
if "all_results" in st.session_state and st.session_state["all_results"]:
    st.write("Search Results:")
    for i, content in enumerate(st.session_state["all_results"], start=1):
        st.text(f"{i}: {content}")
