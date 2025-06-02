▓█████ ██▒   █▓ ██▓███   ▄▄▄       ██▀███   ▄▄▄▄    ▄▄▄█████▓ ██▀███  
▓█   ▀▓██░   █▒▓██▒██▒  ▒████▄    ▓██ ▒ ██▒▓█████▄ ▓  ██▒ ▓▒▓██ ▒ ██▒
▒███   ▓██  █▒░▒██▀██░  ▒██  ▀█▄  ▓██ ░▄█ ▒▒██▒ ▄██▒ ██░ ▒░ ▒██ ░▄█ ▒
▒▓█  ▄  ▒██ █▒░░▓█  ██▓ ░██▄▄▄▄██ ▒██▀▀█▄  ▒██░█▀  ░ ██░     ▒██▀▀█▄  
░▒████▒  ▒▀█░  ░▒▓███▒▓▓ ▓█   ▓██▒░██▓ ▒██▒░▓█  ▀█▓░ ██████▒░██▓ ▒██▒
░░ ▒░ ░  ░ ▐░   ▒░▒   ▒ ▒▒ ▒   ▓▒█░░ ▒▓ ░▒▓░░▒▓███▓▒ ▒░▓  ░░ ▒▓ ░▒▓░
 ░ ░  ░  ░ ░░   ░ ░   ░  ░ ░   ▒ ▒   ░▒ ░ ▒░▒░▒   ▒░ ░ ▒  ░  ░▒ ░ ▒░
   ░       ░░   ░  ░      ░   ▒     ░░   ░  ░ ░   ░  ░   ░   ░░   ░ 
   ░  ░    ░                 ░  ░   ░        ░     ░      ░  ░ 
           ░                                  ░                 

# EcoSort Industrial - Sistema de Clasificación de Residuos v1.0

## Descripción General

EcoSort Industrial es un sistema automatizado para la clasificación de residuos en un entorno industrial utilizando una banda transportadora. El sistema emplea inteligencia artificial (IA) para identificar y clasificar diferentes tipos de residuos (metal, plástico, vidrio, cartón, y otros), y luego utiliza actuadores controlados por un PLC para desviar los materiales clasificados a sus tolvas correspondientes.

Este proyecto está diseñado como una solución integral que incluye:

*   **Detección y Clasificación por IA:** Utiliza un modelo YOLO (actualmente configurado para YOLOv12 o compatible con Ultralytics) para el reconocimiento de objetos en tiempo real.
*   **Control de Banda y Actuadores:** Se comunica con un PLC industrial (vía Modbus TCP/IP) para gestionar el movimiento de la banda transportadora y la activación de los mecanismos de desviación.
*   **Monitoreo de Sensores:** Integra sensores para el disparo de la cámara y la medición del nivel de llenado de las tolvas.
*   **Interfaz de Usuario y Monitoreo Remoto:** Proporciona una API RESTful y WebSockets (construida con Flask y Flask-SocketIO) para el monitoreo en tiempo real, visualización de estadísticas, y control básico del sistema desde una interfaz web.
*   **Registro y Análisis de Datos:** Almacena datos de clasificación, eventos del sistema y estadísticas de operación en una base de datos SQLite para análisis y generación de reportes.

## Arquitectura del Sistema

El sistema se compone de los siguientes módulos principales:

1.  **`main_sistema_banda.py`**: Orquestador principal del sistema. Controla el flujo de detección, clasificación y desviación. Inicializa y coordina todos los demás módulos.
2.  **`IA_Clasificacion/`**:
    *   `TrashDetect.py`: Módulo para la detección de objetos utilizando el modelo YOLO entrenado.
    *   `Train_YOLO.py`: Script para entrenar (o re-entrenar) el modelo YOLO con un dataset personalizado.
    *   `models/`: Directorio para almacenar los modelos de IA entrenados (ej: `best.pt`).
    *   `dataset_basura/`: Directorio (placeholder) para el dataset de imágenes y anotaciones (se espera un `data.yaml` aquí para el entrenamiento).
3.  **`Control_Banda/`**:
    *   `config_industrial.json`: Archivo de configuración central para todos los parámetros del sistema.
    *   **`RPi_control_bajo_nivel/`**:
        *   `conveyor_belt_controller.py`: Controla el motor de la banda transportadora (si no es vía PLC).
        *   `motor_driver_interface.py`: (Actualmente no utilizado directamente por `main_sistema_banda.py` si los actuadores son 100% PLC). Interfaz para controlar actuadores de desviación directamente desde la Raspberry Pi (ej: motores a pasos, solenoides).
        *   `sensor_interface.py`: Maneja la lectura de sensores (disparo de cámara, nivel de tolvas ultrasónicos HC-SR04).
    *   **`plc_logic/`**: Directorio (placeholder) para la lógica del PLC (ej: `LOGO_Main_Program.lsc`).
4.  **`Comunicacion/`**:
    *   `rpi_plc_interface.py`: Módulo para la comunicación Modbus TCP/IP entre la Raspberry Pi y el PLC.
5.  **`InterfazUsuario_Monitoreo/`**:
    *   **`Backend/`**:
        *   `app.py`: Punto de entrada para iniciar el servidor Flask/SocketIO.
        *   `api.py`: Define los endpoints de la API REST y los manejadores de eventos de SocketIO.
        *   `database.py`: Gestiona la base de datos SQLite para el registro de datos y estadísticas.
        *   `data/`: Directorio donde se almacena el archivo de la base de datos (ej: `ecosort_industrial.db`).
    *   **`Frontend/`**: (No implementado en este backend) Directorio destinado a los archivos de la interfaz de usuario web (HTML, CSS, JavaScript).

## Características Clave

*   **Clasificación Automatizada:** Reduce la necesidad de clasificación manual.
*   **Control Centralizado y Remoto:** Permite el monitoreo y control del sistema a través de una interfaz web.
*   **Integración con PLC:** Utiliza un PLC para el control robusto de la maquinaria industrial.
*   **Registro Detallado:** Mantiene un historial de clasificaciones, eventos y rendimiento para análisis y optimización.
*   **Modularidad:** Diseño modular que facilita la expansión y el mantenimiento.
*   **Configurabilidad:** Parámetros del sistema fácilmente ajustables a través de un archivo JSON.

## Requisitos de Hardware

*   Raspberry Pi (se recomienda Pi 4 o Pi 5 para el procesamiento de IA).
*   Cámara compatible con OpenCV (ej: Cámara USB, Módulo de Cámara Raspberry Pi).
*   PLC con capacidad de comunicación Modbus TCP/IP.
*   Sensores:
    *   Sensor de detección de objetos para el disparo de la cámara (ej: fotocelda, sensor infrarrojo).
    *   Sensores ultrasónicos (HC-SR04 o similar) para medir el nivel de las tolvas.
*   Actuadores de desviación (controlados por el PLC).
*   Banda transportadora industrial.
*   Fuente de alimentación adecuada para todos los componentes.

## Requisitos de Software

*   Sistema Operativo: Raspberry Pi OS (o similar Linux).
*   Python 3.7+.
*   Dependencias listadas en `requirements_rpi.txt`.
*   (Opcional, para entrenamiento) Un entorno con GPU (NVIDIA recomendada) para entrenar el modelo YOLOv8.

## Instalación

1.  **Clonar el repositorio:**
    ```bash
    git clone <URL_DEL_REPOSITORIO>
    cd EcoSort-Industrial-Tesis-3A
    ```

2.  **Configurar el entorno virtual (recomendado):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # En Linux/macOS
    # venv\Scripts\activate    # En Windows
    ```

3.  **Instalar dependencias en la Raspberry Pi:**
    ```bash
    pip install -r requirements_rpi.txt
    ```
    *Nota: La instalación de `ultralytics` y `opencv` puede requerir dependencias adicionales del sistema. Consulta sus respectivas documentaciones.*
    *Para `RPi.GPIO`, asegúrate de estar en una Raspberry Pi.*

4.  **Configurar el Modelo de IA:**
    *   Entrena tu modelo YOLOv12 (o la versión que uses de Ultralytics) para tus clases de residuos específicas.
    *   Coloca el modelo entrenado (ej: `best.pt`) en la carpeta `IA_Clasificacion/models/`.
    *   Asegúrate de que el archivo `IA_Clasificacion/dataset_basura/data.yaml` (o el que uses) refleje tus clases y rutas de dataset si vas a re-entrenar.

5.  **Configurar el Archivo `Control_Banda/config_industrial.json`:**
    *   **Este es un paso CRÍTICO.** Ajusta los parámetros de la cámara, modelo de IA, banda transportadora, PLC (IP, puerto), sensores (pines BCM), y actuadores según tu hardware y configuración de red.
    *   Revisa cuidadosamente la sección `plc_settings`, `sensors_settings`, `conveyor_belt_settings` y `diverter_control_settings`.
    *   Presta especial atención a los pines BCM correctos para los sensores y cualquier control GPIO local.

## Uso

### 1. Iniciar el Backend de Monitoreo (Opcional, pero recomendado)

Este servidor proporciona la API y WebSockets para la interfaz de usuario.

```bash
python InterfazUsuario_Monitoreo/Backend/app.py
```

Por defecto, estará disponible en `http://<IP_RASPBERRY_PI>:5000`.

### 2. Iniciar el Sistema Principal de Clasificación

Este es el script principal que controla toda la lógica de la banda transportadora.

```bash
python main_sistema_banda.py
```

*   El sistema intentará conectarse al PLC según la configuración.
*   Si el PLC no está disponible, preguntará si deseas continuar en modo local (control limitado).
*   Los logs de operación se mostrarán en la consola y se guardarán (según configuración de logging).

### 3. (Opcional) Entrenar el Modelo de IA

Si necesitas entrenar o re-entrenar tu modelo de detección:

```bash
python IA_Clasificacion/Train_YOLO.py --data IA_Clasificacion/dataset_basura/data.yaml --model yolov8n.pt --epochs 100 --imgsz 640
```
*Ajusta los parámetros según sea necesario. Se recomienda realizar el entrenamiento en una máquina con GPU.* 

## Estructura de Archivos y Carpetas Clave

```
EcoSort-Industrial-Tesis-3A/
├── Comunicacion/
│   └── rpi_plc_interface.py        # Lógica de comunicación con PLC (Modbus)
├── Control_Banda/
│   ├── RPi_control_bajo_nivel/     # Control de hardware a bajo nivel (sensores, motores RPi)
│   │   ├── conveyor_belt_controller.py
│   │   ├── motor_driver_interface.py
│   │   └── sensor_interface.py
│   └── config_industrial.json      # Archivo de configuración principal
├── IA_Clasificacion/
│   ├── models/                     # Modelos YOLO entrenados (ej: best.pt)
│   ├── dataset_basura/             # Dataset para entrenamiento (data.yaml, images/, labels/)
│   ├── TrashDetect.py              # Script/Clase para realizar detecciones
│   └── Train_YOLO.py               # Script para entrenar modelos YOLO
├── InterfazUsuario_Monitoreo/
│   ├── Backend/
│   │   ├── api.py                  # API Flask y lógica de WebSockets
│   │   ├── app.py                  # Punto de entrada del servidor backend
│   │   ├── database.py             # Gestión de base de datos SQLite
│   │   └── data/                   # Almacén para el archivo .db (ej: ecosort_industrial.db)
│   └── Frontend/                   # (Placeholder) Archivos de la interfaz web (HTML, CSS, JS)
├── captures/                       # (Opcional) Directorio para guardar imágenes capturadas
├── reports/                        # (Opcional) Directorio para guardar reportes generados
├── main_sistema_banda.py           # Orquestador principal del sistema
├── requirements_rpi.txt            # Dependencias de Python para la RPi
├── README.md                       # Este archivo
└── .gitignore                      # Archivos a ignorar por Git
```

## Próximos Pasos y Mejoras Potenciales

*   **Desarrollar la Interfaz de Usuario Frontend:** Crear una interfaz web amigable utilizando los datos proporcionados por la API y WebSockets.
*   **Seguridad Mejorada:** Implementar un sistema de autenticación más robusto para la API (ej: JWT).
*   **Calibración Avanzada:** Añadir rutinas de calibración para la cámara, distancias de actuadores, y velocidad de la banda.
*   **Manejo de Errores y Resiliencia:** Mejorar la capacidad del sistema para recuperarse de fallos (ej: reconexión automática a PLC, reintentos).
*   **Notificaciones Avanzadas:** Integrar notificaciones por correo electrónico o SMS para alertas críticas (ej: tolva llena, error del sistema).
*   **Optimización del Modelo de IA:** Experimentar con diferentes arquitecturas YOLO, técnicas de aumento de datos y post-procesamiento para mejorar la precisión y velocidad.
*   **Control de Velocidad Dinámico:** Ajustar la velocidad de la banda dinámicamente según la carga de objetos.
*   **Mantenimiento Predictivo:** Utilizar los datos almacenados para predecir necesidades de mantenimiento.

## Contribuciones

Este proyecto es parte de una tesis. Por el momento, las contribuciones externas no están activamente solicitadas, pero el feedback es bienvenido.

## Agradecimientos

Queremos expresar nuestro más sincero agradecimiento a las siguientes personas e instituciones por su invaluable apoyo y orientación a lo largo del desarrollo de este proyecto de tesis:

*   **Colegio Español Padre Arrupe:** Por brindarnos la formación académica y los recursos necesarios.
*   **Melquisedec Pérez:** Nuestro tutor, por su constante guía, paciencia y conocimientos expertos que fueron fundamentales para la culminación de este trabajo.
*   A los profesores y personal de las materias de **Práctica III, Tecnología III, Laboratorio de Creatividad III y Trabajo de Graduación**, por su apoyo y por impulsar nuestro aprendizaje en las áreas clave de este proyecto.

## Detalles de Tesis

Este proyecto ha sido desarrollado como parte de los requisitos para las siguientes asignaturas:

*   Práctica III
*   Tecnología III
*   Laboratorio de Creatividad III
*   Trabajo de Graduación

## Autores

*   Gabriel Calderón
*   Elias Bautista
*   Cristian Hernandez

## Licencia

(Considera añadir una licencia si es apropiado, ej: MIT, Apache 2.0)

---
*Junio de 2025* 