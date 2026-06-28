FROM python:3.14-slim

# Runtime libs: libmagic (python-magic), 7z + zip (sample archive handling),
# libxml2/libxslt (+ toolchain) so lxml builds when no cp314 wheel is published.
RUN apt-get -qq update && apt-get install -y --no-install-recommends \
        libmagic1 \
        p7zip-full \
        zip \
        curl \
        gcc \
        libxml2-dev \
        libxslt1-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /crits

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x docker-entrypoint.sh

EXPOSE 8080
ENTRYPOINT ["./docker-entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8080"]
