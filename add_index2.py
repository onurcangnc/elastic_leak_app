from elasticsearch import Elasticsearch, helpers
import os
import time

# Elasticsearch connection
es = Elasticsearch("http://193.164.4.35:9200").options(request_timeout=100)

index_name = "leaks"
files_to_upload = [r"C:/Users/Onurcan/Documents/Projects/elastic/cloudxurl168.txt"]

def ensure_index_exists(index_name):
    if not es.indices.exists(index=index_name):
        es.indices.create(index=index_name, body={
            "mappings": {
                "properties": {
                    "content": {"type": "text"},
                    "file_name": {"type": "keyword"},
                    "line_number": {"type": "integer"},
                }
            }
        })
        print(f"Index '{index_name}' created.")
    else:
        print(f"Index '{index_name}' already exists.")

def bulk_index_file(file_path, index_name):
    actions = []
    encoding_used = "utf-8"

    # Attempt to open the file with utf-8 encoding
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            total_lines = sum(1 for _ in file)
        print(f"Using utf-8 encoding for '{file_path}'.")
    except UnicodeDecodeError:
        # If utf-8 fails, fall back to ISO-8859-1
        try:
            with open(file_path, 'r', encoding='ISO-8859-1') as file:
                total_lines = sum(1 for _ in file)
            encoding_used = "ISO-8859-1"
            print(f"Using ISO-8859-1 encoding for '{file_path}'.")
        except Exception as e:
            print(f"Error reading file '{file_path}': {e}")
            return

    start_time = time.time()

    with open(file_path, 'r', encoding=encoding_used) as file:
        for line_number, line in enumerate(file, start=1):
            content = line.strip()
            if not content:
                continue

            actions.append({
                "_index": index_name,
                "_source": {
                    "content": content,
                    "file_name": os.path.basename(file_path),
                    "line_number": line_number
                }
            })

            if len(actions) >= 200000:  # Smaller chunk size
                try:
                    helpers.bulk(es, actions)
                    actions = []
                    elapsed_time = time.time() - start_time
                    print(f"Processed: {line_number}/{total_lines} "
                          f"({(line_number / total_lines) * 100:.2f}%) | Elapsed: {elapsed_time:.2f}s")
                except Exception as e:
                    print(f"Error during bulk upload: {e}")

        if actions:
            try:
                helpers.bulk(es, actions)
            except Exception as e:
                print(f"Error uploading remaining actions: {e}")

    elapsed_time = time.time() - start_time
    print(f"File '{file_path}' indexed successfully in {elapsed_time:.2f} seconds.")

ensure_index_exists(index_name)

for file_path in files_to_upload:
    print(f"Uploading {file_path}...")
    bulk_index_file(file_path, index_name)
    print(f"Finished uploading {file_path}.")
