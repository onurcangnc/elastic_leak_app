from elasticsearch import Elasticsearch

def delete_index(es_host, index_name):
    es = Elasticsearch(es_host)

    # İndeks silme
    if es.indices.exists(index=index_name):
        response = es.indices.delete(index=index_name)
        print(f"İndeks '{index_name}' silindi.")
    else:
        print(f"İndeks '{index_name}' bulunamadı.")

# Elasticsearch host ve indeks adı
es_host = "http://VDS_IP_ADRESI:9200"
index_name = "leaks_index"

delete_index(es_host, index_name)
