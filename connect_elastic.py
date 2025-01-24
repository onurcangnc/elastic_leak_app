from elasticsearch import Elasticsearch

es = Elasticsearch("http://193.164.4.35:9200/")

if es.ping():
    print("Elasticsearch'e başarıyla bağlanıldı!")
else:
    print("Elasticsearch'e bağlanılamadı.")
