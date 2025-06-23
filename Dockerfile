FROM python:3.11-slim

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    && apt-get clean

# Define diretório de trabalho
WORKDIR /app

# Copia arquivos do projeto
COPY . /app

# Instala dependências Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && jupyter server extension enable voila --sys-prefix

# Variáveis de ambiente para timeout de inatividade
ENV SERVERAPP_KERNEL_IDLE_TIMEOUT = 1800

# Expõe a porta do Voila
EXPOSE 8866

# Comando padrão
CMD ["voila", "--no-browser", "--port=8866", "--Voila.ip=0.0.0.0", "BTCerti_app.ipynb"]

