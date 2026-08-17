"""Flask application entry point."""

from __future__ import annotations

from flask import Flask, jsonify
from flask_cors import CORS

from src.config import Config
from src.routes.disease import disease_bp
from src.routes.filters import filters_bp
from src.routes.hospital import hospital_bp
from src.routes.patient import patient_bp


def create_app() -> Flask:
    """Create and configure the medical BI Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)
    CORS(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}})
    app.register_blueprint(filters_bp)
    app.register_blueprint(patient_bp)
    app.register_blueprint(hospital_bp)
    app.register_blueprint(disease_bp)

    @app.get("/api/health")
    def health_check():
        return jsonify({"code": 0, "message": "success", "data": {"status": "ok"}})

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
