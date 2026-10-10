# Sistema de Gestión de Tareas

Caso Práctico 101 — *Fundamentos de Ingeniería de Software* (MIS 101)
Maestría en Ingeniería de Software — CESUMA Universidad

## Descripción del proyecto

Aplicación de consola escrita en Python que permite **crear, editar, eliminar,
listar y filtrar tareas**. Cada tarea tiene un nombre, una descripción, una
fecha de vencimiento y un estado (`pendiente`, `en progreso`, `completada`).
Las tareas se guardan en un archivo JSON, por lo que se conservan entre
ejecuciones.

El sistema ofrece dos formas de uso:

- **Menú interactivo**: se abre al ejecutar el programa sin argumentos y guía
  al usuario paso a paso.
- **Comandos directos**: para uso rápido o automatizado desde la terminal.

### Funcionalidades

| Requerimiento | Menú | Comando |
|---------------|------|---------|
| Crear tarea | Opción 1 | `crear -n NOMBRE -f AAAA-MM-DD [-d DESC] [-e ESTADO]` |
| Editar tarea | Opción 2 | `editar ID [-n] [-d] [-f] [-e]` |
| Eliminar tarea | Opción 3 | `eliminar ID` |
| Listar tareas | Opción 4 | `listar [-e ESTADO]` |
| Filtrar por estado | Opción 5 | `filtrar ESTADO` |
| Ver detalle (adicional) | Opción 6 | `ver ID` |

Además, las tareas vencidas que no están completadas se marcan como
`(vencida)`.

## Requisitos

- Python **3.10 o superior**
- Sin dependencias externas: solo se usa la biblioteca estándar.

## Cómo ejecutar

```bash
git clone https://github.com/vprada25/case-study-101.git
cd case-study-101
python3 main.py
```

En Windows use `python` en lugar de `python3`.

### Ejemplos con comandos directos

```bash
python3 main.py crear -n "Estudiar Scrum" -f 2026-10-20 -d "Tema 3"
python3 main.py listar
python3 main.py editar 1 -e "en progreso"
python3 main.py filtrar pendiente
python3 main.py eliminar 1
python3 main.py --help
```

Por defecto los datos se guardan en `tasks.json` en el directorio actual.
Se puede usar otro archivo con `--archivo RUTA` o con la variable de entorno
`TASKS_FILE`.

El manual completo está en [docs/manual_usuario.md](docs/manual_usuario.md).

## Cómo ejecutar las pruebas

```bash
python3 -m unittest discover -s tests -v
```

El proyecto tiene **93 pruebas**: 85 unitarias y 8 de integración, con una
cobertura de código del 97 %. Los detalles están en
[docs/pruebas.md](docs/pruebas.md).

## Estructura del proyecto

```
case-study-101/
├── main.py                    # Punto de entrada: python3 main.py
├── task_manager/
│   ├── __main__.py            # Permite: python3 -m task_manager
│   ├── models.py              # Entidad Task y enum TaskStatus
│   ├── service.py             # Lógica de negocio (casos de uso)
│   ├── repository.py          # Persistencia: memoria y JSON
│   ├── exceptions.py          # Excepciones del dominio
│   ├── cli.py                 # Comandos directos (argparse)
│   └── interactive.py         # Menú interactivo
├── tests/
│   ├── test_models.py         # Pruebas unitarias por módulo
│   ├── test_service.py
│   ├── test_repository.py
│   ├── test_cli.py
│   ├── test_interactive.py
│   └── test_integration.py    # Pruebas de integración
└── docs/
    ├── planificacion.md       # Cronograma, estimación y riesgos
    ├── arquitectura.md        # Diseño y decisiones técnicas
    ├── manual_usuario.md      # Guía de uso
    └── pruebas.md             # Estrategia y resultados de pruebas
```

## Documentación

| Documento | Contenido |
|-----------|-----------|
| [Planificación](docs/planificacion.md) | Desglose de tareas, estimación, cronograma y riesgos |
| [Arquitectura](docs/arquitectura.md) | Capas, diagrama de clases y decisiones de diseño |
| [Manual de usuario](docs/manual_usuario.md) | Uso del menú y de los comandos |
| [Pruebas](docs/pruebas.md) | Estrategia, inventario y resultados de las pruebas |

## Autor

Victor Alejandro Prada Noreña — Maestría en Ingeniería de Software, CESUMA.
