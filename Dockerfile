FROM python:3.12-slim
WORKDIR /app
COPY server.py safefetch.py doorcheck.py ./
COPY data/ data/
COPY public/ public/
RUN useradd -r -u 10001 app && mkdir /data && chown app /data
USER app
ENV DATA_DIR=/data PORT=8080
EXPOSE 8080
CMD ["python3", "-u", "server.py"]
