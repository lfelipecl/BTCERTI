FROM python:3.11-slim

WORKDIR /app

# Copia dependências e instala
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copia todo o restante do app (inclusive notebook)
COPY . .

# Comando para rodar o Voila no Fly.io
CMD ["voila", "--port=8080", "--no-browser", "--Voila.base_url=/", "--Voila.enable_nbextensions=True", "BTCerti_app.ipynb"]
