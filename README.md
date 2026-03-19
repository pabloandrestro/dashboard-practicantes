# 🚀 Dashboard de Practicantes - Célula 12

Este proyecto utiliza **Docker** y **WSL 2** para estandarizar el entorno de desarrollo. Esto asegura que todos los miembros del equipo utilicemos las mismas versiones de Python, librerías y dependencias, eliminando errores de compatibilidad entre Windows, Linux o macOS.

---

## 📋 Prerrequisitos

Antes de comenzar, asegúrate de tener instalado en tu sistema:

1. **Docker Desktop**: [Descargar aquí](https://www.docker.com/products/docker-desktop/). 
   * *Importante:* Descargar la version ADM64 y durante la instalación, asegúrate de marcar la opción **"Use recommended settings (WSL 2)"**.
2. **Git**: Para clonar el repositorio.
3. **WSL 2 Actualizado**: Abre una terminal como administrador y ejecuta:
   ```bash
   wsl --update
🛠️ **Configuración Inicial (Solo la primera vez)**

*Clonar el repositorio:*

    git clone [URL_DEL_REPOSITORIO]
    cd dashboard-practicantes

*Preparar variables de entorno:*

Docker necesita un archivo .env para configurar el proyecto. 

Copia el archivo de ejemplo:

    cp .env.example .env

(Si estás en Windows y el comando falla, simplemente duplica el archivo .env.example manualmente y cámbiale el nombre a .env).

📦 **Cómo levantar el proyecto**

Para construir la imagen del contenedor e instalar todas las dependencias (Django, Pillow, uv, etc.), ejecuta el siguiente comando en la raíz del proyecto:

    docker-compose up --build

¿Qué está pasando internamente?
Se crea una burbuja de Linux (Alpine) con Python 3.12,
uv sincroniza las librerías exactas del archivo uv.lock, y
se ejecutan las migraciones automáticamente, se vincula el servidor al puerto 8000 y 
se ejecuta la "imagen" de docker.

🌐 **Acceso al Dashboard**

Una vez que veas en los logs de la terminal el mensaje Starting development server at http://0.0.0.0:8000/, abre tu navegador en:

👉 http://localhost:8000

Y listo, ya estas dentro del proyecto!

-----------------------------

##  🔑 **Comandos Útiles de Docker**

Si necesitas interactuar con el contenedor mientras está corriendo, usa estos comandos:

Crear un Superusuario:

    docker-compose exec web uv run python manage.py createsuperuser
    
🚀 Uso Diario (Flujo de trabajo)

Una vez que ya realizaste la construcción inicial, no necesitas usar `--build` a menos que agregues una nueva librería en el `pyproject.toml`.

### 1. Iniciar el proyecto
Para encender el Dashboard y empezar a trabajar:

    docker-compose up

Aplicar nuevas Migraciones: (Si alguien actualizó los modelos de la base de datos)

    docker-compose exec web uv run python manage.py migrate

Detener el proyecto
Si quieres liberar recursos de tu PC sin borrar los contenedores:

    docker-compose stop
Reiniciar el proyecto si el servidor de Django se queda pegado o necesitas refrescar los servicios:

    docker-compose restart

Apagar y Limpiar (Recomendado antes de apagar la PC)
Para detener los servicios y eliminar los contenedores de la memoria RAM:

Detener el entorno (Cierre limpio):

Primero rresiona Ctrl + C en la terminal y luego ejecuta:

    docker-compose down
