FROM ghcr.io/aziz-rakhimov/tilawa-base:mfa-2.2.17

USER root
WORKDIR /app

COPY ./api/requirements.txt /app/api/requirements.txt
RUN pip install --no-cache-dir -r /app/api/requirements.txt \
    && pip install --no-cache-dir \
       faster-whisper praat-parselmouth noisereduce webrtcvad-wheels \
    && conda run -n aligner pip install 'joblib>=1.4.0,<1.5.0'

RUN python -c \
    "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='float32')"

COPY ./ /app

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["/bin/sh", "-c", "uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
