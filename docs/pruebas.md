# Pruebas: Estrategia y Resultados

## 1. Estrategia

Las pruebas se escribieron **a medida que se desarrollaba cada funcionalidad**:
cada commit del historial incluye el código y sus pruebas. Se usa
exclusivamente `unittest`, de la biblioteca estándar de Python.

```
             ▲  Integración (8)
            ╱ ╲   Sistema completo con archivos reales y procesos
           ╱───╲
          ╱     ╲  Unitarias (85)
         ╱───────╲   Cada módulo aislado, con dobles en memoria
```

| Nivel | Objetivo | Técnica |
|-------|----------|---------|
| **Unitarias** | Verificar cada módulo de forma aislada | Repositorio en memoria (`InMemoryTaskRepository`), flujos `StringIO`, entradas simuladas |
| **Integración** | Verificar que las capas funcionan juntas | Archivo JSON real en un directorio temporal, ejecución del programa como subproceso |

Principios aplicados:

- **Aislamiento**: cada prueba crea su propio servicio o directorio temporal
  (`tempfile.TemporaryDirectory`), por lo que no depende de otras ni deja
  archivos.
- **Determinismo**: se usan fechas lejanas (`2099-12-31`) o fechas de
  referencia explícitas, para que el resultado no dependa del día en que se
  ejecuten.
- **Casos felices y de error**: cada operación se prueba con datos válidos,
  datos inválidos y recursos inexistentes.

## 2. Cómo ejecutar las pruebas

```bash
# Todas las pruebas
python3 -m unittest discover -s tests -v

# Un módulo específico
python3 -m unittest tests.test_service -v

# Una clase o prueba concreta
python3 -m unittest tests.test_cli.TestCrear.test_create_minimal
```

Medición de cobertura (opcional, requiere `pip install coverage`):

```bash
coverage run --source=task_manager -m unittest discover -s tests
coverage report -m
```

## 3. Inventario de pruebas

### 3.1 Pruebas unitarias (85)

| Archivo | Clase | Nº | Qué verifica |
|---------|-------|---:|--------------|
| `test_models.py` | `TestTaskStatus` | 3 | Conversión de texto a estado: tolerante a mayúsculas y separadores, rechaza valores desconocidos |
| | `TestParseDate` | 3 | Fechas ISO válidas; rechazo de `31/12/2026`, `2026-13-01`, vacío o texto |
| | `TestTask` | 7 | Estado por defecto, normalización, nombre vacío, estado inválido, `is_overdue`, serialización ida y vuelta |
| `test_service.py` | `TestCreateTask` | 4 | Ids incrementales, estado inicial, persistencia; datos inválidos no consumen id |
| | `TestUpdateTask` | 6 | Edición parcial y total, borrar descripción, edición inválida conserva la original, id inexistente |
| | `TestDeleteTask` | 3 | Eliminación, id inexistente, ids no reutilizados |
| | `TestListAndFilter` | 5 | Orden por id, lista vacía, filtro por enum y texto, estado inválido, `get_task` |
| | `TestServiceLoadsFromRepository` | 1 | Carga de tareas existentes y continuidad de ids |
| `test_repository.py` | `TestInMemoryTaskRepository` | 2 | Guardar y cargar; aislamiento de la copia |
| | `TestJsonTaskRepository` | 9 | Archivo inexistente, ida y vuelta, formato UTF-8, creación de carpetas, sin temporales sueltos, archivo dañado (no se sobrescribe), ruta no escribible |
| `test_cli.py` | `TestCrear` | 6 | Creación mínima y completa, fecha inválida, nombre vacío, argumentos faltantes, estado inválido |
| | `TestEditar` | 5 | Edición de campos, borrar descripción, sin campos, id inexistente, id inválido |
| | `TestEliminar` | 2 | Eliminación e id inexistente |
| | `TestListarFiltrarVer` | 7 | Listado completo y por estado, filtro, filtro sin resultados, estado inválido, detalle |
| | `TestGeneral` | 3 | Sin comando abre el menú, comando desconocido, `--help` |
| | `TestFormatTable` | 3 | Tabla vacía, marca de vencida, alineación de columnas |
| `test_interactive.py` | `TestMenu` | 5 | Opciones visibles, resumen por estado, opción inválida, salida con Ctrl+D y Ctrl+C |
| | `TestCreate` | 2 | Creación con valores por defecto; reintento ante nombre, fecha y estado inválidos |
| | `TestEdit` | 4 | Enter conserva valores, edición completa, id inexistente, sin tareas |
| | `TestDelete` | 2 | Eliminación confirmada y cancelada |
| | `TestListFilterShow` | 3 | Listar, filtrar por número de estado, ver detalle |

### 3.2 Pruebas de integración (8)

| Clase | Nº | Escenario |
|-------|---:|-----------|
| `TestServiceWithJsonRepository` | 1 | Tres instancias sucesivas del servicio sobre el mismo archivo: los datos y la secuencia de ids sobreviven a los reinicios |
| `TestCliWithJsonFile` | 4 | Ciclo completo crear → editar → filtrar → eliminar → listar con un archivo real; una operación fallida no modifica el archivo; un archivo dañado se informa y se preserva; lo creado desde el menú se guarda en el archivo |
| `TestEndToEndProcess` | 3 | Ejecución real de `python -m task_manager` y `python main.py` como subprocesos: comandos, menú alimentado por la entrada estándar y códigos de salida 0/1/2 |

## 4. Resultados

**Entorno:** Python 3.14.3 · macOS 26.6 · fecha de ejecución 2026-10-10

```
$ python3 -m unittest discover -s tests
.............................................................................................
----------------------------------------------------------------------
Ran 93 tests in 0.242s

OK
```

| Tipo | Ejecutadas | Exitosas | Fallidas | Errores |
|------|-----------:|---------:|---------:|--------:|
| Unitarias | 85 | 85 | 0 | 0 |
| Integración | 8 | 8 | 0 | 0 |
| **Total** | **93** | **93** | **0** | **0** |

### Cobertura de código

```
Name                          Stmts   Miss  Cover
-------------------------------------------------
task_manager/__init__.py          1      0   100%
task_manager/__main__.py          4      4     0%  (*)
task_manager/cli.py             116      0   100%
task_manager/exceptions.py        6      0   100%
task_manager/interactive.py     147      5    97%
task_manager/models.py           51      0   100%
task_manager/repository.py       48      3    94%
task_manager/service.py          42      0   100%
-------------------------------------------------
TOTAL                           415     12    97%
```

(*) `__main__.py` sí se ejecuta en las pruebas de integración, pero como
subproceso, y `coverage` no mide subprocesos con la configuración por
defecto.

Las líneas no cubiertas corresponden a:

- la limpieza del archivo temporal cuando falla la escritura a mitad de
  proceso (`repository.py`), un caso difícil de provocar de forma portable;
- el manejo genérico de errores dentro del bucle del menú y un reintento ante
  un id no numérico (`interactive.py`).

## 5. Defectos críticos que protegen las pruebas

Algunas pruebas se diseñaron específicamente para evitar errores que suelen
aparecer en este tipo de sistemas y que podrían reaparecer en cambios futuros
(pruebas de regresión):

| Defecto que se previene | Prueba que lo detectaría | Mecanismo de diseño |
|-------------------------|--------------------------|---------------------|
| Una edición con un valor inválido deja la tarea a medio modificar | `test_invalid_update_keeps_original` | Se construye una copia validada con `dataclasses.replace` antes de reemplazar la original |
| Un intento de creación inválido consume un id | `test_invalid_data_does_not_consume_id_or_persist` | El contador de ids se incrementa solo después de crear la tarea correctamente |
| Un archivo JSON dañado termina sobrescrito con una lista vacía | `test_corrupt_file_is_not_overwritten_on_load` | `load()` lanza `StorageError` en lugar de devolver `[]` |
| Un guardado interrumpido deja un archivo truncado | `test_no_temp_files_left_behind` | Escritura atómica con archivo temporal y `os.replace` |
