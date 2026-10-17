"""Petite app web : face swap d'une photo vers un GIF animé.

Lancer :  python app.py   puis ouvrir http://localhost:7860
"""

import os
import shutil
import tempfile
import threading
import uuid

from flask import Flask, jsonify, request, send_file, send_from_directory

from swapper import SWAPPERS, FaceSwapper

app = Flask(__name__, static_folder="static")
app.config["MAX_CONTENT_LENGTH"] = 50 * 1024 * 1024

WORK_DIR = tempfile.mkdtemp(prefix="faceswap-gif-")
jobs = {}
swapper = None
swapper_lock = threading.Lock()


def get_swapper():
    global swapper
    with swapper_lock:
        if swapper is None:
            swapper = FaceSwapper()
        return swapper


def run_job(job_id, source, gif, options):
    job = jobs[job_id]
    try:
        job["status"] = "running"
        out = os.path.join(WORK_DIR, f"{job_id}.gif")

        def progress(done, total):
            job["done"], job["total"] = done, total

        get_swapper().process_gif(source, gif, out, progress=progress, **options)
        job.update(status="done", result=out)
    except Exception as exc:  # surfaced to the UI
        job.update(status="error", error=str(exc))
    finally:
        for path in (source, gif):
            if os.path.exists(path):
                os.remove(path)


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/models")
def models():
    return jsonify(list(SWAPPERS))


@app.post("/api/swap")
def swap():
    if "source" not in request.files or "gif" not in request.files:
        return jsonify(error="Il faut une photo source et un GIF."), 400
    job_id = uuid.uuid4().hex
    source = os.path.join(WORK_DIR, f"{job_id}_src")
    gif = os.path.join(WORK_DIR, f"{job_id}_in.gif")
    request.files["source"].save(source)
    request.files["gif"].save(gif)

    form = request.form
    options = {
        "model": form.get("model", "hyperswap_1b_256"),
        "all_faces": form.get("all_faces") == "true",
        "enhance": form.get("enhance", "true") == "true",
        "strength": min(max(float(form.get("strength", 0.8)), 0.0), 1.0),
        "max_side": min(max(int(form.get("max_side", 720)), 128), 1920),
    }
    jobs[job_id] = {"status": "queued", "done": 0, "total": 0}
    threading.Thread(target=run_job, args=(job_id, source, gif, options), daemon=True).start()
    return jsonify(id=job_id)


@app.get("/api/jobs/<job_id>")
def job_status(job_id):
    job = jobs.get(job_id)
    if job is None:
        return jsonify(error="Tâche inconnue."), 404
    return jsonify({k: v for k, v in job.items() if k != "result"})


@app.get("/api/jobs/<job_id>/result")
def job_result(job_id):
    job = jobs.get(job_id)
    if not job or job.get("status") != "done":
        return jsonify(error="Résultat pas encore prêt."), 404
    return send_file(job["result"], mimetype="image/gif", download_name="faceswap.gif")


if __name__ == "__main__":
    import atexit

    atexit.register(shutil.rmtree, WORK_DIR, ignore_errors=True)
    threading.Thread(target=get_swapper, daemon=True).start()  # warm up models in the background
    port = int(os.environ.get("PORT", 7860))
    print(f"\n  → Ouvre http://localhost:{port} dans ton navigateur\n")
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=port, threaded=True)
