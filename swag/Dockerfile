# Use uma imagem base do Python
FROM python:3.10

# Defina a variável de ambiente para que o Python não grave .pyc no disco
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Defina o diretório de trabalho
WORKDIR /code

# Copie o arquivo de requisitos e instale as dependências
COPY requirements.txt /code/
RUN pip install -r requirements.txt

# Copie todo o código da aplicação
COPY . .