"""
FastAPI REST API for Quranic Recitation Assessment.

Single endpoint that accepts an audio file and returns a clean,
frontend-friendly JSON assessment report.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# Ensure project root is on sys.path so pipeline imports work
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from phase3_assessment.multi_ayah_pipeline import assess_recitation  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Configuration from environment ───────────────────────────────────
API_KEY_ENV = "TILAWA_API_KEY"
ALLOWED_ORIGINS_ENV = "TILAWA_ALLOWED_ORIGINS"

_expected_api_key = os.environ.get(API_KEY_ENV)
if not _expected_api_key:
    logger.warning(
        "%s environment variable is not set — API key authentication is DISABLED "
        "(local development mode).",
        API_KEY_ENV,
    )

_allowed_origins_raw = os.environ.get(ALLOWED_ORIGINS_ENV)
if _allowed_origins_raw:
    _allowed_origins = [o.strip() for o in _allowed_origins_raw.split(",") if o.strip()]
else:
    _allowed_origins = ["*"]
    logger.warning(
        "%s environment variable is not set — allowing ALL origins (local development mode).",
        ALLOWED_ORIGINS_ENV,
    )

# ── File validation constants ────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 50 * 1024 * 1024  # 50 MB
ALLOWED_EXTENSIONS = {".wav", ".m4a", ".mp3", ".aac", ".mp4", ".ogg"}

# Magic-byte signatures for allowed audio/container formats.
# Each entry is (offset, bytes_pattern) — the file is accepted if ANY pattern matches.
AUDIO_MAGIC_SIGNATURES = [
    (0, b"RIFF"),          # WAV (RIFF....WAVE)
    (0, b"ID3"),           # MP3 with ID3v2 tag
    (0, b"\xff\xfb"),      # MP3 frame sync (MPEG-1 Layer 3)
    (0, b"\xff\xf3"),      # MP3 frame sync (MPEG-2 Layer 3)
    (0, b"\xff\xf2"),      # MP3 frame sync
    (0, b"\xff\xf1"),      # AAC ADTS
    (0, b"\xff\xf9"),      # AAC ADTS
    (0, b"OggS"),          # OGG
    (4, b"ftyp"),          # MP4/M4A (ISO base media — "ftyp" at offset 4)
]


def _is_valid_audio_magic(header: bytes) -> bool:
    """Return True if the header matches any known audio/container signature."""
    for offset, pattern in AUDIO_MAGIC_SIGNATURES:
        if header[offset : offset + len(pattern)] == pattern:
            return True
    # Additionally verify RIFF files are WAVE (RIFF....WAVE at offset 8)
    # Already covered above by RIFF prefix match, so no separate check needed.
    return False


# ── Rate limiter and app ─────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Quranic Recitation Assessment API")
app.state.limiter = limiter
# Trust Railway's proxy so rate limiting uses real client IP
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware
app.add_middleware(ProxyHeadersMiddleware, trusted_hosts="*")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "X-API-Key"],
)


# ── Exception handlers (safe, non-leaking responses) ─────────────────
@app.exception_handler(RateLimitExceeded)
async def _rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(status_code=429, content={"error": "Too many requests"})


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException):
    # exc.detail is always a short human-readable string we control.
    return JSONResponse(status_code=exc.status_code, content={"error": exc.detail})


@app.exception_handler(Exception)
async def _generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"error": "Assessment failed — please try again"},
    )


# ── API key dependency ───────────────────────────────────────────────
def verify_api_key(x_api_key: Optional[str] = Header(default=None)) -> None:
    """Verify the X-API-Key header against TILAWA_API_KEY.

    If TILAWA_API_KEY is not set in the environment, authentication is skipped
    (local development mode).
    """
    if not _expected_api_key:
        return  # Auth disabled
    if not x_api_key or x_api_key != _expected_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


# ── Quran text loader for word position lookup ───────────────────────
_quran_lookup: dict[tuple[int, int], list[str]] | None = None


def _get_ayah_words(surah: int, ayah: int) -> list[str]:
    """Return the list of words for a given surah/ayah from quran_hafs.json."""
    global _quran_lookup
    if _quran_lookup is None:
        quran_path = Path(PROJECT_ROOT) / "data" / "quran_text" / "quran_hafs.json"
        with open(quran_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _quran_lookup = {}
        for s in data["surahs"]:
            for a in s["ayahs"]:
                text = unicodedata.normalize("NFC", a["text"])
                text = text.replace("\u0640", "")
                _quran_lookup[(s["number"], a["number"])] = text.split()
    return _quran_lookup.get((surah, ayah), [])


# ── Human-readable rule names ────────────────────────────────────────
RULE_DISPLAY_NAMES: dict[str, str] = {
    "madd_tabii": "Madd Tabii",
    "madd_muttasil": "Madd Muttasil",
    "madd_munfasil": "Madd Munfasil",
    "madd_lazim": "Madd Lazim",
    "madd_lazim_kalimi": "Madd Lazim Kalimi",
    "madd_arid_lissukun": "Madd Arid Lissukun",
    "madd_leen": "Madd Leen",
    "madd_badal": "Madd Badal",
    "madd_silah_kubra": "Madd Silah Kubra",
    "madd_silah_sughra": "Madd Silah Sughra",
    "ghunnah_mushaddadah_noon": "Ghunnah (Shaddah on Noon)",
    "ghunnah_mushaddadah_meem": "Ghunnah (Shaddah on Meem)",
    "ghunnah_idgham_with_ghunnah": "Ghunnah (Idgham with Ghunnah)",
    "qalqalah": "Qalqalah",
    "qalqalah_with_shaddah": "Qalqalah (with Shaddah)",
    "ikhfa_haqiqi": "Ikhfa Haqiqi",
    "ikhfa_shafawi": "Ikhfa Shafawi",
    "ikhfa_meem_saakin": "Ikhfa Meem Saakin",
    "emphatic_backing": "Emphatic Backing",
    "pharyngeal_backing": "Pharyngeal Backing",
    "tafkhim": "Tafkhim",
}


def _human_rule_name(rule: str) -> str:
    if rule in RULE_DISPLAY_NAMES:
        return RULE_DISPLAY_NAMES[rule]
    return rule.replace("_", " ").title()


def _build_fix(rule: str, description: str, expected: float, actual: float, unit: str) -> str:
    if unit == "counts":
        if actual < expected:
            return f"Hold the sound longer — aim for {expected:.1f} counts"
        return f"Shorten the sound — aim for {expected:.1f} counts"
    if "backing" in rule or "tafkhim" in rule:
        if actual < expected:
            return "Pronounce with more emphasis — raise the back of the tongue"
        return "Reduce emphasis — lower the back of the tongue slightly"
    if "ghunnah" in rule:
        if actual < expected:
            return f"Sustain the nasal sound longer — aim for {expected:.1f} counts"
        return f"Shorten the nasal sound — aim for {expected:.1f} counts"
    if "qalqalah" in rule:
        return "Add a slight bounce/echo when releasing the letter"
    if "ikhfa" in rule:
        return "Blend the noon/meem sound partially into the next letter with nasalization"
    return description


def _build_mistake(description: str, actual: float, unit: str) -> str:
    desc = description
    bracket = desc.find(" [")
    if bracket != -1:
        desc = desc[:bracket]
    return desc


def _find_word_position(word_text: str, ayah_words: list[str]) -> int:
    def strip_harakat(s: str) -> str:
        return "".join(
            c for c in unicodedata.normalize("NFD", s)
            if unicodedata.category(c) not in ("Mn",)
        )

    target = strip_harakat(word_text)
    for i, w in enumerate(ayah_words):
        if strip_harakat(w) == target:
            return i
    for i, w in enumerate(ayah_words):
        if target in strip_harakat(w) or strip_harakat(w) in target:
            return i
    return 0


_WORD_ERROR_NOTES = {
    "wrong":   "Tajweed assessment skipped for this word",
    "missing": "Word was not recited — Tajweed assessment skipped",
    "added":   "Extra word not in Quran text",
}


def _transform_response(raw: dict) -> dict:
    surah = raw["surah"]
    start_ayah = raw["start_ayah"]
    end_ayah = raw["end_ayah"]
    overall_score = raw["overall_score"]
    total_errors = raw["total_errors"]

    wv = raw.get("word_verification", {})
    wv_by_ayah: dict[int, dict] = {}
    for va in wv.get("ayahs", []):
        wv_by_ayah[va["ayah"]] = va

    total_word_errors = wv.get("total_word_errors", 0)
    word_error_type_counts: Counter[str] = Counter()

    all_rule_counts: Counter[str] = Counter()
    ayahs_out = []

    for ayah_data in raw.get("ayahs", []):
        ayah_num = ayah_data["ayah"]
        ayah_words = _get_ayah_words(surah, ayah_num)

        errors_out = []
        for err in ayah_data.get("errors", []):
            severity = err.get("severity", "minor")
            if severity not in ("minor", "major"):
                continue

            rule_key = err.get("rule", "")
            word_text = err.get("word", "")
            expected = err.get("expected", 0)
            actual = err.get("actual", 0)
            unit = err.get("unit", "")
            description = err.get("description", "")

            word_pos = _find_word_position(word_text, ayah_words)

            human_rule = _human_rule_name(rule_key)
            all_rule_counts[human_rule] += 1

            errors_out.append({
                "word": word_text,
                "word_position": word_pos,
                "rule": human_rule,
                "mistake": _build_mistake(description, actual, unit),
                "fix": _build_fix(rule_key, description, expected, actual, unit),
                "severity": severity,
            })

        word_errors_out = []
        va_data = wv_by_ayah.get(ayah_num, {})
        for we in va_data.get("word_errors", []):
            etype = we.get("error_type", "wrong")
            word_error_type_counts[etype] += 1
            word_errors_out.append({
                "type": etype,
                "word_position": we.get("word_position"),
                "expected": we.get("expected_word"),
                "detected": we.get("detected_word"),
                "severity": "major",
                "note": _WORD_ERROR_NOTES.get(etype, ""),
            })

        assessed = ayah_data.get("phones_assessed", 0)
        passed = ayah_data.get("phones_passed", 0)
        ayah_score = round((passed / max(assessed, 1)) * 100, 1)

        ayahs_out.append({
            "ayah": ayah_num,
            "score": ayah_score,
            "errors": errors_out,
            "word_errors": word_errors_out,
        })

    most_common = all_rule_counts.most_common(1)
    most_common_error = most_common[0][0] if most_common else None
    errors_per_rule = dict(all_rule_counts)

    return {
        "surah": surah,
        "start_ayah": start_ayah,
        "end_ayah": end_ayah,
        "overall_score": overall_score,
        "total_errors": total_errors,
        "total_word_errors": total_word_errors,
        "ayahs": ayahs_out,
        "summary": {
            "most_common_error": most_common_error,
            "errors_per_rule": errors_per_rule,
            "word_error_counts": {
                "wrong": word_error_type_counts.get("wrong", 0),
                "missing": word_error_type_counts.get("missing", 0),
                "added": word_error_type_counts.get("added", 0),
            },
        },
    }


# ── Audio conversion helper ──────────────────────────────────────────
def _convert_to_wav(input_path: str, output_path: str) -> None:
    """Convert input audio to 16kHz mono PCM WAV using ffmpeg.

    Raises HTTPException(422) if ffmpeg is not installed or conversion fails.
    """
    if shutil.which("ffmpeg") is None:
        logger.error("ffmpeg binary not found on PATH")
        raise HTTPException(
            status_code=422,
            detail="Audio conversion failed — unsupported format",
        )
    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-ar", "16000",
        "-ac", "1",
        "-c:a", "pcm_s16le",
        output_path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg conversion timed out for %s", input_path)
        raise HTTPException(
            status_code=422,
            detail="Audio conversion failed — unsupported format",
        )
    except Exception:
        logger.exception("ffmpeg invocation failed")
        raise HTTPException(
            status_code=422,
            detail="Audio conversion failed — unsupported format",
        )
    if result.returncode != 0:
        logger.error(
            "ffmpeg returned non-zero (%d). stderr: %s",
            result.returncode,
            result.stderr.decode("utf-8", errors="replace")[:2000],
        )
        raise HTTPException(
            status_code=422,
            detail="Audio conversion failed — unsupported format",
        )


# ── Endpoints ────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/assess/recitation")
@limiter.limit("10/minute")
async def assess(
    request: Request,
    file: UploadFile = File(...),
    surah: int = Form(...),
    start_ayah: int = Form(...),
    end_ayah: int = Form(...),
    _auth: None = Depends(verify_api_key),
):
    """Assess a Quranic recitation from an uploaded audio file."""

    # ── Input validation: surah / ayah range ─────────────────────────
    if surah < 1 or surah > 114:
        raise HTTPException(
            status_code=422,
            detail="surah must be between 1 and 114",
        )
    if start_ayah < 1:
        raise HTTPException(
            status_code=422,
            detail="start_ayah must be >= 1",
        )
    if end_ayah < start_ayah:
        raise HTTPException(
            status_code=422,
            detail="end_ayah must be >= start_ayah",
        )
    if (end_ayah - start_ayah) > 20:
        raise HTTPException(
            status_code=422,
            detail="No more than 20 ayahs may be assessed in one request",
        )

    # ── File validation: extension ───────────────────────────────────
    if not file.filename:
        raise HTTPException(status_code=400, detail="Unsupported file format")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Unsupported file format")

    # ── Read the file (streamed, with size cap) ──────────────────────
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=400, detail="File too large")

    # ── File validation: magic bytes ─────────────────────────────────
    if not _is_valid_audio_magic(content[:16]):
        raise HTTPException(status_code=400, detail="Unsupported file format")

    upload_path: Optional[str] = None
    converted_path: Optional[str] = None
    try:
        # Save uploaded content to a temp file (preserving extension for ffmpeg)
        with tempfile.NamedTemporaryFile(
            suffix=ext, delete=False, prefix="recitation_upload_",
        ) as tmp:
            upload_path = tmp.name
            tmp.write(content)

        # Determine the WAV path to feed into the pipeline
        if ext == ".wav":
            wav_for_pipeline = upload_path
        else:
            with tempfile.NamedTemporaryFile(
                suffix=".wav", delete=False, prefix="recitation_converted_",
            ) as tmp_wav:
                converted_path = tmp_wav.name
            _convert_to_wav(upload_path, converted_path)
            wav_for_pipeline = converted_path

        # Run the pipeline
        try:
            raw_result = assess_recitation(
                wav_path=wav_for_pipeline,
                surah=surah,
                start_ayah=start_ayah,
                end_ayah=end_ayah,
            )
        except HTTPException:
            raise
        except Exception:
            logger.exception("Pipeline error during assessment")
            raise HTTPException(
                status_code=500,
                detail="Assessment failed — please try again",
            )

        response = _transform_response(raw_result)
        return JSONResponse(content=response)

    finally:
        # Always clean up both temp files, even on crashes
        for p in (upload_path, converted_path):
            if p and os.path.exists(p):
                try:
                    os.unlink(p)
                except OSError:
                    logger.warning("Failed to remove temp file", exc_info=True)
