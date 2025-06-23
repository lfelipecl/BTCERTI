FROM python:3.11-slim

WORKDIR /app

# Copia requirements.txt antes para usar cache do Docker melhor
COPY requirements.txt /app/

# Atualiza pip e instala os pacotes, incluindo voila via requirements.txt
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && jupyter server extension enable voila --sys-prefix

# Copia todo o código depois que as libs já foram instaladas
COPY . /app

EXPOSE 8080

CMD ["voila", "BTCerti_app.ipynb", "--port=8080", "--no-browser", "--Voila.ip=0.0.0.0"]

