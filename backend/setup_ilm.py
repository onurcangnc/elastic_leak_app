from elasticsearch import Elasticsearch
import urllib3

# Self-signed sertifika uyarılarını kapat
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Elasticsearch bağlantısı (HTTPS + auth + certs kapalı)
es = Elasticsearch(
    ["https://localhost:9200"],
    basic_auth=("elasticuser", "elasticuser_password"),
    verify_certs=False,
    request_timeout=100
)

# 1. ILM policy
es.ilm.put_lifecycle(
    name="leaks_policy",
    body={
        "policy": {
            "phases": {
                "hot": {
                    "min_age": "0ms",
                    "actions": {
                        "rollover": {
                            "max_size": "5gb",
                            "max_age": "1d"
                        }
                    }
                },
                "delete": {
                    "min_age": "5d",  # ✅ Günde 1 kez silme isteğin burada
                    "actions": {"delete": {}}
                }
            }
        }
    }
)
print("✅ ILM policy oluşturuldu.")

# 2. Index template
es.indices.put_index_template(
    name="leaks_template",
    body={
        "index_patterns": ["leaks-*"],
        "template": {
            "settings": {
                "index.lifecycle.name": "leaks_policy",
                "index.lifecycle.rollover_alias": "leaks",
                "number_of_shards": 1
            },
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "file_name": {"type": "keyword"},
                    "line_number": {"type": "integer"}
                }
            }
        }
    }
)
print("✅ Index template oluşturuldu.")

# 3. İlk index ve alias
es.indices.create(
    index="leaks-000001",
    body={
        "aliases": {
            "leaks": {
                "is_write_index": True
            }
        }
    }
)
print("✅ İlk index leaks-000001 ve alias leaks oluşturuldu.")
