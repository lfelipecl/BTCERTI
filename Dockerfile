FROM python:3.11-slim

WORKDIR /app

# Copia requirements.txt para instalar pacotes
COPY requirements.txt /app/

# Atualiza pip e instala os pacotes, incluindo o voila explicitamente
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && pip install --no-cache-dir voila \
    && jupyter server extension enable voila --sys-prefix

# Copia todo o código para o container
COPY . /app

# Expõe a porta padrão do Voila
EXPOSE 8866

# Comando para rodar o Voila apontando para o notebook principal (ajuste se precisar)
CMD ["voila", "BTCerti_app.ipynb", "--port=8866", "--no-browser", "--Voila.ip=0.0.0.0"]
