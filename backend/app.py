from flask import Flask, request, jsonify, render_template, redirect, url_for, send_file, session
from elasticsearch import Elasticsearch
import urllib3
import os
import uuid
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from datetime import timedelta
from waitress import serve

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__, template_folder="templates")
app.secret_key = "gizli-bir-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=20)

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.init_app(app)

@login_manager.unauthorized_handler
def unauthorized():
    if request.accept_mimetypes.accept_json:
        return jsonify({"error": "Oturum süresi dolmuş. Lütfen tekrar giriş yapın."}), 401
    return redirect(url_for("login"))

@app.before_request
def redirect_unauthorized():
    session.modified = False
    if not current_user.is_authenticated and request.endpoint not in ["login", "static", "health", "search_api"] and not request.path.startswith("/static"):
        return redirect(url_for("login"))

limiter = Limiter(key_func=get_remote_address, app=app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    def check_password(self, password):
        return bcrypt.check_password_hash(self.password_hash, password)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

es = Elasticsearch(
    ["https://127.0.0.1:9200"],
    basic_auth=("elasticuser", "elasticpassword"),
    verify_certs=False,
    ca_certs="C:/Users/Administrator/Desktop/leak/elasticsearch-8.17.1/config/certs/node-1.crt",
    request_timeout=1800,
    max_retries=3,
    retry_on_timeout=True,
)

@app.route("/login", methods=["GET", "POST"])
@limiter.limit("5 per minute")
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.permanent = True
            session.modified = False
            login_user(user, remember=False)
            return redirect(url_for("home"))
        return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/")
@login_required
def home():
    return render_template("index.html")

@app.route("/search_api", methods=["POST"])
@login_required
def search_api():
    data = request.get_json()
    query = data.get("q", "").strip()
    search_after = data.get("search_after")

    if not query:
        return jsonify({"error": "Boş sorgu"}), 400

    def build_body(search_after=None):
        body = {
            "query": {
                "wildcard": {
                    "content": {
                        "value": f"*{query}*"
                    }
                }
            },
            "_source": ["content", "file_name", "line_number"],
            "sort": ["line_number"]
        }
        if search_after:
            body["search_after"] = search_after
        return body

    try:
        count_body = {
            "query": {
                "wildcard": {
                    "content": {
                        "value": f"*{query}*"
                    }
                }
            }
        }
        total = es.count(index="leaks-*", body=count_body)["count"]

        if total <= 10000:
            body = build_body()
            response = es.search(index="leaks-*", body=body, size=10000)
            results = []
            for hit in response["hits"]["hits"]:
                src = hit["_source"]
                line = f"{src.get('file_name', 'unknown')}:{src.get('line_number', 'N/A')} → {src['content']}"
                results.append(line)

            filename = "results.txt"
            with open(filename, "w", encoding="utf-8") as f:
                for line in results:
                    f.write(line + "\n")

            return jsonify({"mode": "download", "download_url": f"/download/{filename}"})

        # else > 10000
        response = es.search(index="leaks-*", body=build_body(search_after), size=10000)
        hits = response["hits"]["hits"]
        results = []
        for hit in hits:
            src = hit["_source"]
            line = f"{src.get('file_name', 'unknown')}:{src.get('line_number', 'N/A')} → {src['content']}"
            results.append(line)
        next_sort = hits[-1]["sort"] if hits else None
        return jsonify({"mode": "paginate", "results": results, "next_sort": next_sort})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/download/<path:filename>")
@login_required
def serve_download(filename):
    try:
        response = send_file(filename, as_attachment=True)

        @response.call_on_close
        def cleanup():
            try:
                os.remove(filename)
            except Exception as e:
                print(f"[!] Dosya silinemedi: {e}")

        return response
    except Exception as e:
        return f"Hata: {e}", 500

@app.route("/health", methods=["GET"])
def health():
    try:
        if es.ping():
            return jsonify({"status": "Elasticsearch is reachable"})
        else:
            return jsonify({"status": "Elasticsearch is not reachable"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    serve(app, host="0.0.0.0", port=8501, threads=8, connection_limit=2000, asyncore_loop_timeout=3000, channel_timeout=300)
