import logging
import sys
from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch

app = Flask(__name__)

# Elasticsearch Bağlantısı
ELASTICSEARCH_URL = "http://localhost:9200"
es = Elasticsearch(
    [ELASTICSEARCH_URL],
    verify_certs=False,
    request_timeout=360,  # Uzun sorgular için arttırılmış timeout
    max_retries=10,
    retry_on_timeout=True
)

# Loglama Ayarları: sadece konsola yazma
logging.basicConfig(
    level=logging.INFO,  # Dosyaya yazmak için 'filename' parametresi kaldırıldı
    format="%(asctime)s - %(levelname)s - [%(message)s]"
)

# Konsola yazan bir stream handler ekliyoruz.
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(levelname)s - [%(message)s]")
console_handler.setFormatter(formatter)
logging.getLogger("").addHandler(console_handler)

@app.route("/search", methods=["GET"])
def search():
    query = request.args.get("q")
    page_size = 10000
    search_after = request.args.getlist("search_after")

    if not query:
        logging.info("Received search request without query parameter.")
        return jsonify({"error": "Query parameter is required"}), 400

    logging.info("Received search query: %s", query)

    try:
        # Wildcard sorgusu ile "content.keyword" üzerinde arama yapıyoruz
        search_query = {
            "query": {
                "wildcard": {
                    "content.keyword": {
                        "value": f"*{query}*"
                    }
                }
            },
            "size": page_size,
            "sort": [{"line_number": "asc"}]
        }

        if search_after:
            search_query["search_after"] = search_after

        logging.info("Executing search query: %s", search_query)
        result = es.search(
            index="leaks,leaks-*",
            body=search_query,
            _source=["content", "line_number"]
        )

        hits = result["hits"]["hits"]
        next_search_after = hits[-1]["sort"] if hits else None

        response_data = {
            "results": [hit["_source"]["content"] for hit in hits if "_source" in hit],
            "total_results": result["hits"]["total"]["value"],
            "search_after": next_search_after
        }

        logging.info("Search completed. Total results: %s", response_data["total_results"])
        return jsonify(response_data)

    except Exception as e:
        logging.error("Error during search: %s", str(e))
        return jsonify({"error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    try:
        if es.ping():
            return jsonify({"status": "Elasticsearch is running"}), 200
        return jsonify({"status": "Elasticsearch is down"}), 500
    except Exception as e:
        logging.error("Health Check Failed: %s", str(e))
        return jsonify({"status": "Error", "message": str(e)}), 500

if __name__ == "__main__":
    # 0.0.0.0 ile tüm arayüzlerden erişilebilir,
    # gerekliyse sadece localhost (127.0.0.1) kullanılabilir.
    app.run(host="0.0.0.0", port=5000)
