# Usa imagem oficial Python slim para reduzir tamanho
FROM python:3.11-slim

# Define diretório de trabalho dentro do container
WORKDIR /app

# Copia requirements.txt para instalar dependências
COPY requirements.txt .

# Atualiza pip e instala dependências sem cache para manter imagem leve
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Copia todo o código da aplicação para o container
COPY . .

# Expõe a porta que o Dash usa (padrão 8050)
EXPOSE 8050

# Define variável de ambiente para indicar que roda no container
ENV PORT=8050

# Comando para rodar o app
CMD ["python", "app.py"]
