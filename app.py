import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock, Thread
from uuid import uuid4

from flask import Flask, jsonify, render_template, request, send_from_directory

from pwp_bot_service import PWPBotService


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
service = PWPBotService(BASE_DIR)


class JobManager:
    def __init__(self):
        self.jobs = {}
        self.jobs_lock = Lock()
        self.execution_lock = Lock()

    def _now(self):
        return datetime.now(timezone.utc).isoformat()

    def create_job(self, name, target, *args, **kwargs):
        job_id = uuid4().hex
        job = {
            "id": job_id,
            "name": name,
            "status": "queued",
            "message": f"{name} queued.",
            "created_at": self._now(),
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
        }
        with self.jobs_lock:
            self.jobs[job_id] = job

        thread = Thread(target=self._run_job, args=(job_id, target, args, kwargs), daemon=True)
        thread.start()
        return job

    def _run_job(self, job_id, target, args, kwargs):
        self.update_job(job_id, status="running", started_at=self._now(), message="Job is running.")
        try:
            with self.execution_lock:
                result = service.run_exclusive(target, *args, **kwargs)
            self.update_job(
                job_id,
                status="completed",
                finished_at=self._now(),
                message=result.get("message", "Job completed."),
                result=result,
            )
        except Exception as exc:
            self.update_job(
                job_id,
                status="failed",
                finished_at=self._now(),
                message=str(exc),
                error=str(exc),
            )

    def update_job(self, job_id, **updates):
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if not job:
                return
            job.update(updates)

    def get_job(self, job_id):
        with self.jobs_lock:
            job = self.jobs.get(job_id)
            if not job:
                return None
            return dict(job)


jobs = JobManager()


def async_job_response(name, target, *args, **kwargs):
    job = jobs.create_job(name, target, *args, **kwargs)
    return jsonify(
        {
            "ok": True,
            "job_id": job["id"],
            "status": job["status"],
            "message": f"{name} started.",
        }
    )


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/health")
def health():
    return jsonify({"ok": True, "logged_in": service.logged_in})


@app.get("/api/jobs/<job_id>")
def get_job(job_id):
    job = jobs.get_job(job_id)
    if not job:
        return jsonify({"ok": False, "message": "Job not found."}), 404
    return jsonify({"ok": True, **job})


@app.post("/api/login")
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""
    if not email or not password:
        return jsonify({"ok": False, "message": "Email and password are required."}), 400

    try:
        result = service.run_exclusive(service.login, email, password)
        return jsonify({"ok": True, **result})
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.post("/api/validate")
def validate_excel():
    excel_file = request.files.get("excel_file")
    if not excel_file or not excel_file.filename:
        return jsonify({"ok": False, "message": "Excel file is required."}), 400

    try:
        saved_path = service.save_upload(excel_file, "validate")
        return async_job_response("Excel validation", service.validate_excel_file, saved_path)
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.post("/api/data-upload")
def data_upload():
    excel_file = request.files.get("excel_file")
    upload_mode = (request.form.get("upload_mode") or "normal").strip()
    if not excel_file or not excel_file.filename:
        return jsonify({"ok": False, "message": "Excel file is required."}), 400

    try:
        saved_path = service.save_upload(excel_file, "data_upload")
        return async_job_response("Data upload", service.data_upload, saved_path, upload_mode)
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.post("/api/invoice-upload")
def invoice_upload():
    excel_file = request.files.get("excel_file")
    pdf_files = [pdf for pdf in request.files.getlist("pdf_files") if pdf and pdf.filename]
    if not excel_file or not excel_file.filename:
        return jsonify({"ok": False, "message": "Excel file is required."}), 400
    if not pdf_files:
        return jsonify({"ok": False, "message": "At least one PDF is required."}), 400

    try:
        saved_excel = service.save_upload(excel_file, "invoice_upload")
        saved_pdfs = service.save_pdf_uploads(pdf_files)
        return async_job_response("Invoice upload", service.invoice_upload, saved_excel, saved_pdfs)
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.post("/api/delete-upload")
def delete_upload():
    excel_file = request.files.get("excel_file")
    if not excel_file or not excel_file.filename:
        return jsonify({"ok": False, "message": "Excel file is required."}), 400

    try:
        saved_path = service.save_upload(excel_file, "delete_upload")
        return async_job_response("Delete upload data", service.delete_upload_data, saved_path)
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.post("/api/scrape")
def scrape():
    data = request.get_json(silent=True) or {}
    choice = (data.get("choice") or "").strip()
    if not choice:
        return jsonify({"ok": False, "message": "Scrape choice is required."}), 400

    try:
        return async_job_response("Scrape export", service.scrape_data, choice)
    except Exception as exc:
        return jsonify({"ok": False, "message": str(exc)}), 500


@app.get("/files/<path:filename>")
def download_file(filename):
    for directory in (service.output_dir, service.upload_dir):
        file_path = directory / filename
        if file_path.exists():
            return send_from_directory(directory, filename, as_attachment=True)
    return jsonify({"ok": False, "message": "File not found."}), 404


if __name__ == "__main__":
    debug_enabled = os.getenv("FLASK_DEBUG", "0") == "1"
    port = int(os.getenv("PORT", "5000"))
    app.run(debug=debug_enabled, host="0.0.0.0", port=port)
