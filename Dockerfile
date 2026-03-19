# Usamos una imagen de Python ligera con uv preinstalado
FROM ghcr.io/astral-sh/uv:python3.12-alpine

# Directorio de trabajo dentro del contenedor
WORKDIR /app

# Variables de entorno para que Python no genere basura y muestre logs rápido
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Instalamos dependencias del sistema para Pillow (imágenes) y PostgreSQL
RUN apk add --no-cache \
    gcc \
    musl-dev \
    jpeg-dev \
    zlib-dev \
    libpq-dev \
    libffi-dev

# Copiamos archivos de dependencias
COPY pyproject.toml uv.lock ./

# Instalamos las librerías del proyecto
RUN uv sync --frozen --no-cache

# Copiamos todo el código de HubLab al contenedor
COPY . .

# Exponemos el puerto de Django
EXPOSE 8000

# Comando para arrancar el servidor
CMD ["uv", "run", "python", "manage.py", "runserver", "0.0.0.0:8000"]