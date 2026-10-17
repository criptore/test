"""Face swap engine: one source photo -> every frame of an animated GIF.

Pipeline per frame:
  1. detect faces + 5 landmarks (InsightFace SCRFD, buffalo_l)
  2. align each target face on the ArcFace template
  3. run the swapper (HyperSwap 1B 256 by default, or inswapper 128)
  4. optionally restore the swapped face with GFPGAN 1.4
  5. paste back with a soft mask
"""

import os
import threading
import urllib.request

import cv2
import numpy as np
import onnxruntime as ort
from onnx import load as onnx_load, numpy_helper
from PIL import Image, ImageSequence
from insightface.app import FaceAnalysis
from insightface.utils.face_align import estimate_norm

MODELS_DIR = os.environ.get("FACESWAP_MODELS_DIR", os.path.join(os.path.dirname(__file__), "models"))
ASSETS = "https://github.com/facefusion/facefusion-assets/releases/download"

SWAPPERS = {
    "hyperswap_1b_256": {"url": f"{ASSETS}/models-3.3.0/hyperswap_1b_256.onnx", "size": 256, "type": "hyperswap"},
    "inswapper_128": {"url": f"{ASSETS}/models-3.0.0/inswapper_128.onnx", "size": 128, "type": "inswapper"},
}
ENHANCER = {"name": "gfpgan_1.4", "url": f"{ASSETS}/models-3.0.0/gfpgan_1.4.onnx", "size": 512}

# FFHQ 5-point template (normalized) used by GFPGAN.
FFHQ_512 = np.array(
    [[0.37691676, 0.46864664], [0.62285697, 0.46912813], [0.50123859, 0.61331904],
     [0.39308822, 0.72541100], [0.61150205, 0.72490465]], dtype=np.float32) * 512


def providers():
    available = ort.get_available_providers()
    preferred = ["CUDAExecutionProvider", "CoreMLExecutionProvider", "DmlExecutionProvider"]
    return [p for p in preferred if p in available] + ["CPUExecutionProvider"]


def ensure_model(name, url):
    path = os.path.join(MODELS_DIR, name + ".onnx")
    if not os.path.exists(path):
        os.makedirs(MODELS_DIR, exist_ok=True)
        print(f"Téléchargement de {name} ...")
        tmp = path + ".part"
        urllib.request.urlretrieve(url, tmp)
        os.replace(tmp, path)
    return path


def box_mask(size, blur=0.3, padding=0.0):
    """Feathered rectangular mask in crop space (values 0..1)."""
    mask = np.ones((size, size), np.float32)
    blur_px = max(int(size * 0.5 * blur), 1)
    pad = int(size * padding)
    edge = max(blur_px // 2, pad)
    mask[:edge, :] = 0
    mask[-edge:, :] = 0
    mask[:, :edge] = 0
    mask[:, -edge:] = 0
    return cv2.GaussianBlur(mask, (0, 0), blur_px * 0.25)


def paste_back(frame, crop, mask, M):
    h, w = frame.shape[:2]
    IM = cv2.invertAffineTransform(M)
    warped = cv2.warpAffine(crop, IM, (w, h), borderMode=cv2.BORDER_REPLICATE)
    warped_mask = cv2.warpAffine(mask, IM, (w, h))[..., None].clip(0, 1)
    out = warped_mask * warped.astype(np.float32) + (1 - warped_mask) * frame.astype(np.float32)
    return out.clip(0, 255).astype(np.uint8)


class FaceSwapper:
    def __init__(self):
        self.providers = providers()
        self.analyser = FaceAnalysis(name="buffalo_l", allowed_modules=["detection", "recognition"],
                                     providers=self.providers)
        self.analyser.prepare(ctx_id=0, det_size=(640, 640))
        self.sessions = {}
        self.emap = None
        self.lock = threading.Lock()  # one GIF at a time: models are big and CPU-bound

    def _session(self, name, url):
        if name not in self.sessions:
            path = ensure_model(name, url)
            self.sessions[name] = ort.InferenceSession(path, providers=self.providers)
            if name == "inswapper_128":
                graph = onnx_load(path).graph
                self.emap = numpy_helper.to_array(graph.initializer[-1])
        return self.sessions[name]

    def faces(self, bgr):
        return self.analyser.get(bgr)

    def source_embedding(self, bgr):
        faces = self.faces(bgr)
        if not faces:  # tightly cropped portraits: give the detector some context
            pad = max(bgr.shape[:2]) // 2
            faces = self.faces(cv2.copyMakeBorder(bgr, pad, pad, pad, pad, cv2.BORDER_CONSTANT))
        if not faces:
            raise ValueError("Aucun visage détecté sur la photo source.")
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        return face.normed_embedding

    # --- swap --------------------------------------------------------------

    def swap_face(self, frame, kps, embedding, model):
        spec = SWAPPERS[model]
        size = spec["size"]
        session = self._session(model, spec["url"])
        M = estimate_norm(kps, size, "arcface")
        crop = cv2.warpAffine(frame, M, (size, size), borderValue=0.0)
        rgb = crop[:, :, ::-1].astype(np.float32) / 255.0

        if spec["type"] == "inswapper":
            latent = embedding.reshape(1, -1) @ self.emap
            latent /= np.linalg.norm(latent)
            target = rgb.transpose(2, 0, 1)[None]
            out = session.run(None, {"target": target, "source": latent.astype(np.float32)})[0][0]
            out = out.transpose(1, 2, 0).clip(0, 1)
            mask = box_mask(size, blur=0.3, padding=0.05)
        else:  # hyperswap: inputs/outputs in [-1, 1], also predicts a face mask
            target = ((rgb - 0.5) / 0.5).transpose(2, 0, 1)[None]
            out, face_mask = session.run(None, {"target": target.astype(np.float32),
                                                "source": embedding.reshape(1, -1).astype(np.float32)})
            out = (out[0].transpose(1, 2, 0) * 0.5 + 0.5).clip(0, 1)
            face_mask = cv2.GaussianBlur(face_mask[0, 0].clip(0, 1), (0, 0), size / 128)
            mask = np.minimum(face_mask, box_mask(size, blur=0.3))

        swapped = (out[:, :, ::-1] * 255).astype(np.uint8)
        return paste_back(frame, swapped, mask, M)

    def enhance_face(self, frame, kps, strength):
        size = ENHANCER["size"]
        session = self._session(ENHANCER["name"], ENHANCER["url"])
        M = cv2.estimateAffinePartial2D(kps, FFHQ_512, method=cv2.LMEDS)[0]
        crop = cv2.warpAffine(frame, M, (size, size), borderMode=cv2.BORDER_REPLICATE)
        x = ((crop[:, :, ::-1].astype(np.float32) / 255.0 - 0.5) / 0.5).transpose(2, 0, 1)[None]
        out = session.run(None, {"input": x})[0][0].clip(-1, 1)
        out = ((out.transpose(1, 2, 0) + 1) / 2 * 255)[:, :, ::-1]
        restored = (strength * out + (1 - strength) * crop).clip(0, 255).astype(np.uint8)
        return paste_back(frame, restored, box_mask(size, blur=0.3), M)

    def process_frame(self, frame, embedding, model, all_faces, enhance, strength):
        faces = self.faces(frame)
        if not faces:
            return frame
        if not all_faces:
            faces = [max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))]
        for face in faces:
            frame = self.swap_face(frame, face.kps, embedding, model)
            if enhance:
                frame = self.enhance_face(frame, face.kps, strength)
        return frame

    # --- GIF ---------------------------------------------------------------

    def process_gif(self, source_path, gif_path, out_path, model="hyperswap_1b_256", all_faces=False,
                    enhance=True, strength=0.8, max_side=720, progress=None):
        if model not in SWAPPERS:
            raise ValueError(f"Modèle inconnu : {model}")
        source = cv2.imread(source_path)
        if source is None:
            source = cv2.cvtColor(np.array(Image.open(source_path).convert("RGB")), cv2.COLOR_RGB2BGR)

        with self.lock:
            embedding = self.source_embedding(source)
            gif = Image.open(gif_path)
            total = getattr(gif, "n_frames", 1)
            loop = gif.info.get("loop", 0)
            frames, durations = [], []
            for i, frame in enumerate(ImageSequence.Iterator(gif)):
                durations.append(frame.info.get("duration", gif.info.get("duration", 100)) or 100)
                rgb = frame.convert("RGB")
                scale = min(1.0, max_side / max(rgb.size))
                if scale < 1.0:
                    rgb = rgb.resize((round(rgb.width * scale), round(rgb.height * scale)), Image.LANCZOS)
                bgr = cv2.cvtColor(np.array(rgb), cv2.COLOR_RGB2BGR)
                bgr = self.process_frame(bgr, embedding, model, all_faces, enhance, strength)
                frames.append(Image.fromarray(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)))
                if progress:
                    progress(i + 1, total)

        palette_frames = [f.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.FLOYDSTEINBERG)
                          for f in frames]
        palette_frames[0].save(out_path, save_all=True, append_images=palette_frames[1:], duration=durations,
                               loop=loop, disposal=2, optimize=False)
        return out_path
