from elasticsearch import Elasticsearch

es = Elasticsearch(
    ["https://localhost:9200"],
    basic_auth=("elasticuser", "elasticuser_password"),
    verify_certs=False
)

response = es.indices.delete(index="leaks-000001", ignore_unavailable=True)
print("✅ Silme tamamlandı:", response)
