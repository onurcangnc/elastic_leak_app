from elasticsearch import Elasticsearch
from datetime import datetime, timezone
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ========================
# Elasticsearch Ayarları
# ========================
es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elasticuser", "elasticpassword"),
    verify_certs=False,
    request_timeout=100
)

INDEX_PREFIX = "leaks"
ROLLOVER_ALIAS = "leaks"

# ========================
# Yardımcı Fonksiyonlar
# ========================
def calculate_age_days(creation_dt):
    now = datetime.now(timezone.utc)
    return (now - creation_dt).days

# ========================
# Ana Index Tablosu
# ========================
def get_index_status():
    ilm_explains = es.ilm.explain_lifecycle(index=f"{INDEX_PREFIX}-*")
    indices_info = ilm_explains.get("indices", {})

    index_stats = es.cat.indices(index=f"{INDEX_PREFIX}-*", format="json", bytes="gb")
    size_map = {idx["index"]: float(idx.get("store.size", 0)) for idx in index_stats}

    aliases = es.indices.get_alias(name=ROLLOVER_ALIAS, ignore_unavailable=True)
    alias_map = {
        idx: meta["aliases"][ROLLOVER_ALIAS]
        for idx, meta in aliases.items()
        if ROLLOVER_ALIAS in meta.get("aliases", {})
    }

    print(f"{'Index':<22} {'Yazılabilir?':<16} {'Oluşturulma':<24} {'Yaş (gün)':<10} {'Silinmeye Kalan (gün)':<24} {'Silinme Durumu':<16} {'Kullanım (GB)'}")
    print("-" * 135)

    ilm_policies = es.ilm.get_lifecycle()

    for index, data in indices_info.items():
        creation_timestamp = data.get("lifecycle_date_millis")
        if not creation_timestamp:
            continue

        creation_dt = datetime.fromtimestamp(creation_timestamp / 1000, tz=timezone.utc)
        creation_str = creation_dt.strftime("%Y-%m-%d %H:%M:%S")
        age_days = calculate_age_days(creation_dt)

        is_write = alias_map.get(index, {}).get("is_write_index", False)
        ilm_phase = data.get("phase", "")
        policy_name = data.get("policy")

        deletion_status = "⏳ bekliyor"
        if ilm_phase == "delete":
            deletion_status = "🗑️ silinecek"
        elif ilm_phase == "completed":
            deletion_status = "✅ tamamlandı"
        elif is_write:
            deletion_status = "✅ yazılıyor"

        delete_min_age_days = None
        if policy_name and policy_name in ilm_policies:
            delete_phase = ilm_policies[policy_name]["policy"]["phases"].get("delete", {})
            min_age_str = delete_phase.get("min_age", "0d")
            if min_age_str.endswith("d"):
                try:
                    delete_min_age_days = int(min_age_str.rstrip("d"))
                except ValueError:
                    pass

        remaining_days = delete_min_age_days - age_days if delete_min_age_days is not None else "-"
        if isinstance(remaining_days, int):
            remaining_days = max(remaining_days, 0)

        size_gb = size_map.get(index, 0.0)
        print(
            f"{index:<22} {str(is_write):<16} {creation_str:<24} {age_days:<10} {str(remaining_days):<24} {deletion_status:<16} {size_gb:.2f}"
        )

# ========================
# Disk Özeti
# ========================
def print_disk_summary(prefix="leaks"):
    indices = es.cat.indices(index=f"{prefix}-*", format="json", bytes="gb")
    total_size = 0.0
    empty_indices = []

    for idx in indices:
        size = float(idx.get("store.size", 0))
        total_size += size
        if idx.get("docs.count") == "0":
            empty_indices.append(idx["index"])

    print(f"\n📦 Toplam disk kullanımı: {total_size:.2f} GB")
    print(f"🗑️ Boş index sayısı: {len(empty_indices)}")
    if empty_indices:
        print("➡️ Boş indexler:")
        for idx in empty_indices:
            print(f"  - {idx}")

# ========================
# Dosya Bazlı İstatistikler
# ========================
def print_file_stats_per_index():
    print("\n📄 Dosya Bazlı Döküman Sayıları:\n")
    indices = es.cat.indices(index=f"{INDEX_PREFIX}-*", h="index", format="json")
    index_names = [idx["index"] for idx in indices]

    for index_name in index_names:
        agg_query = {
            "size": 0,
            "aggs": {
                "files": {
                    "terms": {
                        "field": "file_name",
                        "size": 100
                    }
                }
            }
        }
        try:
            res = es.search(index=index_name, body=agg_query)
            buckets = res.get("aggregations", {}).get("files", {}).get("buckets", [])
            if not buckets:
                continue

            print(f"📦 Index: {index_name}")
            for bucket in buckets:
                print(f"  - {bucket['key']}: {bucket['doc_count']} döküman")
        except Exception as e:
            print(f"⚠️ {index_name} için sorgu hatası: {e}")

# ========================
# Main
# ========================
if __name__ == "__main__":
    get_index_status()
    print_disk_summary()
    print_file_stats_per_index()
