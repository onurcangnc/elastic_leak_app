from elasticsearch import Elasticsearch, helpers
from tqdm import tqdm
from datetime import datetime, timezone
import os
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

es = Elasticsearch(
    "https://localhost:9200",
    basic_auth=("elasticuser", "elasticuser_password"),
    verify_certs=False,  # Self-signed sertifika kullanıyorsan bu şekilde geçici olarak kapatabilirsin
    request_timeout=100
)

ROLLOVER_ALIAS = "leaks"

def bulk_index_sequential(file_path):
    actions = []
    encoding_used = "utf-8"

    try:
        with open(file_path, 'r', encoding=encoding_used) as f:
            total_lines = sum(1 for _ in f)
    except UnicodeDecodeError:
        encoding_used = "ISO-8859-1"
        with open(file_path, 'r', encoding=encoding_used) as f:
            total_lines = sum(1 for _ in f)

    with open(file_path, 'r', encoding=encoding_used) as f:
        with tqdm(total=total_lines, desc=f"Indexing {os.path.basename(file_path)}", unit="lines") as pbar:
            for line_number, line in enumerate(f, start=1):
                content = line.strip()
                if not content:
                    continue

                actions.append({
                    "_index": ROLLOVER_ALIAS,
                    "_source": {
                        "content": content,
                        "file_name": os.path.basename(file_path),
                        "line_number": line_number,
                        "@timestamp": datetime.now(timezone.utc).isoformat()
                    }
                })

                if len(actions) >= 200000:
                    helpers.bulk(es, actions)
                    pbar.update(len(actions))
                    actions = []

            if actions:
                helpers.bulk(es, actions)
                pbar.update(len(actions))

    print(f"✅ '{file_path}' dosyası '{ROLLOVER_ALIAS}' alias'ına yüklendi.")

# === Ana fonksiyon ===
if __name__ == "__main__":
    current_dir = os.getcwd()
    txt_files = [f for f in os.listdir(current_dir) if f.endswith(".txt")]

    if not txt_files:
        print("❌ Bu klasörde hiç .txt dosyası bulunamadı.")
        exit()

    print("📄 İndexlenecek dosyayı seç:")
    for i, file in enumerate(txt_files, start=1):
        print(f"[{i}] {file}")

    selected_indices = input("👉 İndex numaralarını virgül ile gir (örnek: 1,3): ")
    selected_indices = [int(i.strip()) for i in selected_indices.split(",") if i.strip().isdigit()]

    selected_files = [os.path.join(current_dir, txt_files[i - 1]) for i in selected_indices if 0 < i <= len(txt_files)]

    if not selected_files:
        print("❌ Geçerli bir seçim yapılmadı.")
        exit()

    for file_path in selected_files:
        bulk_index_sequential(file_path)
