# Imagem base leve com Python
FROM python:3.11-slim

# Instalar dependências do sistema (Voila e widgets precisam de alguns)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Criar diretório de trabalho
WORKDIR /code

# Copiar dependências e instalar
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Copiar os arquivos da aplicação
COPY . .

# Comando padrão para iniciar o app com Voila
CMD ["voila", "--port=7860", "--no-browser", "--Voila.base_url=/", "--Voila.enable_nbextensions=True", "BTCerti_app.ipynb"]
