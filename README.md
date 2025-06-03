Este proyecto utiliza **Django** como backend y **Node.js** para gestionar dependencias frontend Tailwind CSS

## ✅ Requisitos previos

Antes de comenzar, asegúrate de tener instalado en tu máquina:

- Python 3.9 o superior
- Node.js y npm
- PostgreSQL (opcional, si deseas usar una base de datos más robusta que SQLite)
- Git (opcional, si clonarás desde un repositorio)

---

## 🚀 Pasos para iniciar el proyecto

### 1. Clonar el repositorio (si aplica)

```bash
git clone https://github.com/anthnnydev/GNAGRO.git
cd tu-repositorio
```


2. Crear y activar entorno virtual
py -m venv env
env\Scripts\activate

3. Instalar dependencias de Node.js
npm install

4. Instalar dependencias de Python
pip install -r requirements.txt

5. Aplicar migraciones
python manage.py makemigrations
python manage.py migrate

6. Ejecutar el servidor de desarrollo
python manage.py runserver
