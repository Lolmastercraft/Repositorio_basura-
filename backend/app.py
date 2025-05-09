# backend/app.py
import os
from pathlib import Path
from datetime import timedelta

from flask import Flask, send_from_directory, session
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

app = Flask(
    __name__,
    static_folder=str(BASE_DIR.parent / "public"),
    static_url_path="/"
)

# ------ claves y sesión ------
app.secret_key = os.getenv("SECRET_KEY", "dev123")
app.permanent_session_lifetime = timedelta(hours=4)  # caduca en 4 h

# ------ Blueprint ------
from routes import api                                        # noqa: E402
app.register_blueprint(api)

# ------ Rutas ------
@app.route("/")
def login():
    return app.send_static_file("login.html")

@app.errorhandler(404)
def not_found(_):
    custom_404 = Path(app.static_folder) / "404.html"
    if custom_404.exists():
        return send_from_directory(app.static_folder, "404.html"), 404
    return {"error": "Página no encontrada"}, 404

if __name__ == "__main__":
    port  = int(os.getenv("FLASK_RUN_PORT", 5000))
    debug = os.getenv("FLASK_ENV") == "development"
    app.run(host="0.0.0.0", port=port, debug=debug)
