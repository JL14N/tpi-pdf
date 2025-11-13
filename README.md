
Proyecto: Demo TPI — PDFs inseguros vs variante aislada y POST

Descripción corta
Este repositorio contiene una demo didáctica que compara dos comportamientos: una variante vulnerable donde un PDF con un enlace puede provocar un cambio de estado (por ejemplo, cambiar el email administrativo), y una variante "segura" que mitiga la técnica aplicando varias medidas (uso de POST para cambios, aislamiento y políticas CSP).

Nota sobre el "merge"
Hemos unificado la experiencia de demostración: ambas variantes están accesibles desde el mismo origen/puerto para facilitar la comparación local. En la documentación se usa `http://127.0.0.1:5000` como base para la demo. Si necesitas ejecutar las dos variantes simultáneamente en la misma máquina, arranca cada script en puertos distintos (p. ej. 5000 y 5001).

Contenido clave
- `vulnerable_server.py`: servidor con comportamiento inseguro para la demo.
- `secure_server.py`: servidor con protecciones aplicadas (POST obligatorio para cambios sensibles, CSP y aislamiento de uploads).
- `templates/`: plantillas compartidas entre ambas variantes.
- `uploads/`: carpetas compartidas entre ambas variantes.
- `admin_state.json`: almacena el `admin_email` usado en la demo.

Por qué usamos un enlace en el PDF en vez de código JavaScript embebido
- Compatibilidad y realismo: la ejecución de JavaScript embebido en PDFs es poco fiable. Muchos visores (y visores integrados en navegadores) deshabilitan o restringen la ejecución de JS en PDFs por seguridad.
- Claridad didáctica: un enlace clickeable muestra de forma determinista cómo un documento puede inducir al usuario a realizar una petición que cambie estado (CSRF vía GET) sin depender de comportamientos específicos del visor.
- Evita dependencias complejas: usar un enlace mantiene la demo reproducible en navegadores y visores sin instalar herramientas adicionales.

Diferencias entre la variante vulnerable y la variante segura
- Método HTTP:
  - Vulnerable: admite GET para `/admin/change-email?email=...` y realiza el cambio. Esto hace trivial explotar la vulnerabilidad desde un enlace en un PDF.
  - Segura: exige POST para cambios de estado, y no permite que un GET realice modificaciones (respuesta 405 o rechazo).
- Aislamiento y almacenamiento:
  - Vulnerable: sirve los PDFs desde `uploads/` en el mismo origen.
  - Segura: también usa `uploads/`, pero aplica cabeceras que limitan el alcance del contenido subido.
- Políticas de seguridad (CSP):
  - Segura: aplica una política CSP para reducir vectores (por ejemplo, limitar `img-src` y `frame-ancestors`).
    Nota: en este repositorio la política se ha relajado temporalmente para permitir estilos inline en las plantillas locales; en producción recomendamos nonces/hashes o ficheros CSS externos.
- Control de acceso:
  - Segura: comprueba el rol (admin/attacker) y evita que un usuario atacante realice cambios administrativos.
- Interfaz y previews:
  - Ambos muestran miniaturas generadas en el servidor para previsualizar PDFs (PNG textual). Para thumbnails exactos de la primera página se necesita `pdftoppm` (Poppler) como dependencia de sistema.

Cómo ejecutar (rápido)
1. (Opcional) crear entorno virtual e instalar dependencias:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
2. Arrancar la variante que quieras probar:
```bash
# Variante vulnerable
python3 vulnerable_server.py

# Variante segura
python3 secure_server.py
```
Nota: la documentación asume `http://127.0.0.1:5000` como base; ajusta el puerto si arrancas instancias en puertos distintos.

Endpoints útiles
- `/login` — página de acceso (credenciales de prueba: `admin/admin` y `attacker/attacker`).
- `/manage` — interfaz del atacante para subir/eliminar PDFs (slots de ejemplo).
- `/sample_csrf_link` — devuelve un PDF de ejemplo con un enlace a `/admin/change-email?...`.
- `/admin/change-email` — endpoint/formulario que cambia el email administrativo (GET en la variante vulnerable, POST en la variante segura).

Recomendaciones finales
- No expongas estas demos a Internet; son para laboratorio.
- Para endurecer la variante segura en producción:
  - Evitar `unsafe-inline` en CSP; usar nonces/hashes o CSS externo.
  - Añadir protección CSRF/CSRF tokens donde proceda y fortalecer la gestión de sesiones.
  - Usar renderizado de thumbnails basado en herramientas dedicadas si necesitas fidelidad visual.

```
