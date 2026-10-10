# Manual de Usuario

## 1. Instalación

1. Instale **Python 3.10 o superior**. Para verificarlo, ejecute
   `python3 --version`.
2. Descargue el proyecto:

   ```bash
   git clone https://github.com/vprada25/case-study-101.git
   cd case-study-101
   ```

No se requiere instalar ninguna librería adicional.

> En Windows reemplace `python3` por `python` en todos los comandos.

## 2. Modo menú interactivo (recomendado)

```bash
python3 main.py
```

Se muestra el menú principal con un resumen de las tareas por estado:

```
============================================
  GESTOR DE TAREAS
  2 tarea(s) — pendiente: 1 | en progreso: 1 | completada: 0
============================================
  1. Crear tarea
  2. Editar tarea
  3. Eliminar tarea
  4. Listar tareas
  5. Filtrar por estado
  6. Ver detalle de una tarea
  0. Salir
Seleccione una opción:
```

Escriba el número de la opción y presione **Enter**.

### 2.1 Crear una tarea (opción 1)

El programa solicita los datos uno por uno:

```
--- Nueva tarea ---
Nombre: Preparar informe
Descripción (opcional): Caso práctico 101
Fecha de vencimiento (AAAA-MM-DD): 2026-10-25
Estados:
  1. pendiente
  2. en progreso
  3. completada
Seleccione un estado [Enter = pendiente]:

✔ Tarea creada con id 1.
```

Si un dato es inválido (nombre vacío, fecha con otro formato, estado
inexistente), se muestra el motivo y se vuelve a preguntar.

### 2.2 Editar una tarea (opción 2)

Se muestra la tabla de tareas y se pide el id. Para cada campo aparece el
valor actual entre corchetes:

- presione **Enter** para conservarlo;
- escriba un nuevo valor para cambiarlo;
- en la descripción, escriba `-` para borrarla.

### 2.3 Eliminar una tarea (opción 3)

Se pide el id y luego una confirmación (`s` / `n`).

### 2.4 Listar (opción 4) y filtrar (opción 5)

```
ID  Nombre            Vence       Estado               Descripción
--  ----------------  ----------  -------------------  -----------------
1   Preparar informe  2026-10-25  pendiente            Caso práctico 101
2   Revisar código    2026-10-01  pendiente (vencida)

Total: 2 tarea(s)
```

Las tareas cuya fecha ya pasó y que no están completadas se marcan como
**(vencida)**.

### 2.5 Salir

Elija `0` o presione **Ctrl+C**. Los cambios ya están guardados: el
programa guarda después de cada operación.

## 3. Modo comandos

Útil para operaciones rápidas o para usar en *scripts*.

```
python3 main.py [--archivo RUTA] <comando> [opciones]
```

| Comando | Descripción | Ejemplo |
|---------|-------------|---------|
| `crear` | Crea una tarea | `python3 main.py crear -n "Leer" -f 2026-11-01 -d "Cap. 3" -e pendiente` |
| `editar` | Modifica solo los campos indicados | `python3 main.py editar 1 -e completada` |
| `eliminar` | Elimina una tarea | `python3 main.py eliminar 1` |
| `listar` | Lista todas las tareas (opcionalmente por estado) | `python3 main.py listar -e "en progreso"` |
| `filtrar` | Lista las tareas de un estado | `python3 main.py filtrar pendiente` |
| `ver` | Muestra el detalle de una tarea | `python3 main.py ver 1` |

**Opciones de `crear` y `editar`:**

| Opción | Significado |
|--------|-------------|
| `-n`, `--nombre` | Nombre de la tarea (obligatorio en `crear`) |
| `-f`, `--fecha` | Fecha de vencimiento `AAAA-MM-DD` (obligatoria en `crear`) |
| `-d`, `--descripcion` | Descripción. En `editar`, `-d ""` la borra. |
| `-e`, `--estado` | `pendiente`, `en progreso` (o `en_progreso`), `completada` |

Use `python3 main.py --help` o `python3 main.py <comando> --help` para ver la
ayuda.

### Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Operación exitosa |
| 1 | Error de datos (id inexistente, fecha inválida, archivo dañado) |
| 2 | Error de uso (comando u opción mal escritos) |

## 4. Archivo de datos

- Por defecto: `tasks.json` en la carpeta desde donde se ejecuta el programa.
- Otro archivo: `--archivo otra_ruta.json` o la variable de entorno
  `TASKS_FILE`.
- Es un archivo de texto legible:

  ```json
  {
    "version": 1,
    "tasks": [
      {
        "id": 1,
        "name": "Preparar informe",
        "description": "Caso práctico 101",
        "due_date": "2026-10-25",
        "status": "pendiente"
      }
    ]
  }
  ```

- Si el archivo se daña, el programa muestra un error y **no lo
  sobrescribe**, para que pueda revisarse o restaurarse.
