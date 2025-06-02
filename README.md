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

![EcoSort Industrial Banner](https://images.unsplash.com/photo-1611284446314-60a58ac0deb9?q=80&w=2070&auto=format&fit=crop&ixlib-rb-4.0.3&ixid=M3wxMjA3fDB8MHxwaG90by1wYWdlfHx8fGVufDB8fHx8fA%3D%3D)

# EcoSort Industrial - Sistema de Clasificación de Residuos v1.0

## Descripción General

EcoSort Industrial es un sistema automatizado para la clasificación de residuos en un entorno industrial utilizando una banda transportadora. El sistema emplea inteligencia artificial (IA) para identificar y clasificar diferentes tipos de residuos (metal, plástico, vidrio, cartón, y otros), y luego utiliza actuadores controlados por un PLC para desviar los materiales clasificados a sus tolvas correspondientes.

Este proyecto está diseñado como una solución integral que incluye:

*   **Detección y Clasificación por IA:** Utiliza un modelo YOLO (actualmente configurado para YOLOv12 o compatible con Ultralytics) para el reconocimiento de objetos en tiempo real.
*   **Control de Banda y Actuadores:** Se comunica con un PLC industrial (vía Modbus TCP/IP) para gestionar el movimiento de la banda transportadora y la activación de los mecanismos de desviación.
*   **Monitoreo de Sensores:** Integra sensores para el disparo de la cámara y la medición del nivel de llenado de las tolvas.
*   **Interfaz de Usuario y Monitoreo Remoto:** Proporciona una API RESTful y WebSockets (construida con Flask y Flask-SocketIO) para el monitoreo en tiempo real, visualización de estadísticas, y control básico del sistema desde una interfaz web.
*   **Registro y Análisis de Datos:** Almacena datos de clasificación, eventos del sistema y estadísticas de operación en una base de datos SQLite para análisis y generación de reportes.

## Planteamiento del Problema

*   En la actualidad, la gestión eficiente de residuos sólidos, especialmente a nivel industrial y en plantas de reciclaje, presenta desafíos significativos en El Salvador y a nivel global. Los procesos de clasificación manual son intensivos en mano de obra, costosos, lentos y pueden exponer a los trabajadores a condiciones insalubres o peligrosas. Además, la clasificación manual a menudo resulta en una menor pureza de los materiales recuperados, lo que disminuye su valor y la eficiencia general del reciclaje. La acumulación de desechos sin una segregación adecuada contribuye a la contaminación ambiental y a la pérdida de recursos valiosos que podrían ser reincorporados a la cadena productiva. Existe una necesidad apremiante de implementar tecnologías de automatización avanzadas que puedan optimizar estos procesos, incrementando la velocidad, precisión y seguridad en la clasificación de desechos industriales, fomentando así una economía circular más efectiva. Este proyecto busca abordar la ineficiencia y los altos costos asociados con la clasificación manual de residuos en flujos industriales, mediante la aplicación de visión artificial e inteligencia artificial en un sistema de banda transportadora.

## Objetivos

### Objetivo General

*   Desarrollar e implementar un prototipo funcional de un sistema automatizado para la clasificación inteligente de desechos (Metal, Vidrio, Plástico, Cartón) en una banda transportadora de escala de laboratorio, utilizando visión por computadora y un modelo de redes neuronales convolucionales (YOLO), orientado a mejorar la eficiencia en procesos industriales de reciclaje.

### Objetivos Específicos

*   Diseñar y construir un prototipo físico de una banda transportadora equipada con un sistema de captura de imágenes (cámara y sistema de iluminación controlada) y mecanismos de desviación para cuatro tipos de desechos.

*   Crear un conjunto de datos (dataset) de imágenes representativo de los desechos a clasificar (Metal, Vidrio, Plástico, Cartón) en condiciones similares a las de la banda transportadora.

*   Entrenar, validar y optimizar un modelo de red neuronal convolucional (YOLO) capaz de identificar y clasificar los tipos de desechos definidos con un nivel de precisión aceptable en tiempo real o cuasi real.

*   Desarrollar un sistema de control (utilizando una Raspberry Pi 5 como unidad central de procesamiento) que integre la captura de imágenes, la inferencia del modelo de IA y la activación sincronizada de los mecanismos de desviación en función de la clasificación obtenida y el movimiento de la banda.

*   Implementar la lógica de sincronización necesaria para asegurar que los actuadores de desviación se activen en el momento preciso en que el objeto clasificado llega al punto de segregación correspondiente en la banda transportadora.

*   Evaluar el rendimiento del prototipo en términos de precisión de clasificación, velocidad de procesamiento (objetos por minuto) y efectividad de la desviación física bajo condiciones controladas de laboratorio.



## Justificación

*   Este proyecto posee una relevancia significativa desde múltiples perspectivas:

Relevancia Tecnológica: Aplica tecnologías de vanguardia como la inteligencia artificial (específicamente redes neuronales convolucionales como YOLO) y la visión por computadora a un problema industrial concreto y actual. La integración de estos componentes en un sistema de banda transportadora para la clasificación autónoma representa una innovación en el campo de la automatización industrial y la robótica aplicada.

Relevancia Industrial y Económica: La automatización de la clasificación de residuos tiene el potencial de transformar las operaciones en plantas de reciclaje y centros de gestión de desechos. Puede conducir a una reducción significativa de los costos operativos (asociados a la mano de obra y a errores de clasificación), un aumento en la eficiencia y velocidad del proceso, y una mejora en la calidad (pureza) de los materiales recuperados, lo que incrementa su valor en el mercado. Esto es particularmente importante para la industria del reciclaje en El Salvador, donde la optimización de costos y la eficiencia son clave.

Relevancia Social y Ambiental: Al mejorar la eficiencia del reciclaje, el proyecto contribuye directamente a la reducción de la cantidad de residuos que terminan en vertederos, mitigando el impacto ambiental asociado. Fomenta la transición hacia una economía circular, donde los materiales se reutilizan y reciclan en lugar de desecharse. Además, la automatización de tareas de clasificación, que a menudo son repetitivas y pueden ser insalubres o peligrosas, puede mejorar las condiciones laborales de los trabajadores del sector.

Relevancia Académica: El desarrollo de este proyecto proporcionará un caso de estudio práctico y valioso sobre la aplicación de técnicas avanzadas de ingeniería de software, hardware e inteligencia artificial. Generará conocimiento aplicable y servirá como base para futuras investigaciones y desarrollos en el área de la automatización industrial y la gestión inteligente de residuos en el contexto local y regional.

## Alcance y Limitaciones

### Alcance

*   Desarrollo de Prototipo: Se construirá un prototipo funcional a escala de laboratorio de un sistema de banda transportadora con capacidad de clasificación automatizada.

Tipos de Residuos: El sistema se enfocará en la clasificación de cuatro categorías principales de desechos predefinidos: Metal, Vidrio, Plástico y Cartón.

Condiciones de Operación: Los objetos se introducirán en la banda de forma individual o con una separación suficiente para permitir su identificación y clasificación individual por el sistema de visión.

Componentes Clave: El proyecto cubrirá el diseño e implementación del sistema de visión (cámara, iluminación), el desarrollo y entrenamiento del modelo de IA, la programación del sistema de control en la Raspberry Pi 5, el diseño y control de los mecanismos de desviación física, y la lógica de sincronización entre estos componentes.

Rendimiento: Se buscará una clasificación y desviación en tiempo real o cuasi real, adecuada para la velocidad de la banda del prototipo.

Interfaz de Usuario: Será una interfaz básica para el monitoreo del estado del sistema y visualización de estadísticas de clasificación.

Plataforma de Control: El control principal y el procesamiento de IA se realizarán en una Raspberry Pi 5. La interacción con actuadores y sensores se gestionará mediante sus pines GPIO y los scripts de Python desarrollados (motor_driver_interface.py, sensor_interface.py, conveyor_belt_controller.py).

### Limitaciones

*   Escala del Prototipo: El sistema desarrollado será un prototipo de laboratorio y no una máquina de grado industrial lista para producción masiva o despliegue inmediato en una planta.

Variabilidad del Dataset: Aunque se buscará un dataset representativo, este será limitado en comparación con la inmensa variabilidad (formas, tamaños, niveles de suciedad, deformaciones, objetos mezclados) de los residuos en un flujo industrial real.

Condiciones Ambientales: El rendimiento se evaluará bajo condiciones de iluminación controlada en el laboratorio. Variaciones extremas de luz o la presencia de polvo y vibraciones en un entorno industrial real podrían afectar el desempeño y no serán exhaustivamente abordadas.

Manejo de Objetos Complejos: El sistema no está diseñado para manejar objetos fuertemente adheridos, superpuestos, excesivamente sucios, o residuos peligrosos/especiales no contemplados en las categorías definidas.

Análisis Exhaustivo: No se incluirá un análisis de costos detallado para la implementación industrial a gran escala, ni pruebas de durabilidad a largo plazo de los componentes mecánicos.

Recursos Computacionales: El procesamiento de IA estará limitado por la capacidad de la Raspberry Pi 5. No se explorarán soluciones basadas en GPUs de alto rendimiento o procesamiento en la nube, a menos que se especifique como una línea de trabajo futuro.

Tiempo y Presupuesto: El desarrollo estará restringido por el cronograma académico y los recursos económicos disponibles para el proyecto de tesis.

## Metodología

*   La metodología para el desarrollo de este proyecto se basará en un enfoque de investigación aplicada y desarrollo tecnológico experimental, siguiendo las siguientes fases:

Fase de Investigación y Planificación:

Revisión bibliográfica exhaustiva sobre sistemas de clasificación de residuos, visión por computadora, redes neuronales convolucionales (especialmente YOLO), control de bandas transportadoras y automatización industrial.

Definición detallada de los requisitos funcionales y técnicos del sistema.

Selección de componentes de hardware (cámara, Raspberry Pi 5, tipo de banda, motores para la banda y desviadores, drivers, sensores de disparo y de nivel, materiales para la estructura).

Diseño conceptual del sistema mecánico y electrónico.

Planificación detallada del proyecto, incluyendo cronograma y asignación de tareas.

Fase de Diseño y Desarrollo de Hardware:

Diseño detallado (CAD si es posible) de la estructura de la banda transportadora, los mecanismos de desviación (ej: compuertas accionadas por motores a pasos o solenoides) y el sistema de montaje para la cámara y la iluminación.

Ensamblaje físico del prototipo de la banda transportadora y los mecanismos de desviación.

Integración de la cámara, el sistema de iluminación, la Raspberry Pi 5, los drivers de motor, y los sensores (sensor de disparo para la cámara, sensores de nivel para las tolvas de destino).

Cableado y pruebas iniciales de cada componente de hardware.

Fase de Desarrollo de Software:

Módulo de Inteligencia Artificial (IA_Clasificacion):

Recolección y preprocesamiento de un conjunto de datos de imágenes de los residuos objetivo (Metal, Vidrio, Plástico, Cartón).

Anotación de las imágenes para el entrenamiento del modelo YOLO.

Entrenamiento, validación y ajuste fino del modelo YOLO utilizando Python y librerías como PyTorch/TensorFlow y OpenCV.

Desarrollo de TrashDetect.py para la inferencia en tiempo real.

Módulos de Control de Bajo Nivel (Control_Banda/RPi_control_bajo_nivel):

Desarrollo de sensor_interface.py para leer el sensor de disparo de la cámara y los sensores de nivel de las tolvas.

Desarrollo de motor_driver_interface.py para controlar los actuadores de los mecanismos de desviación.

Desarrollo de conveyor_belt_controller.py para el encendido/apagado y (opcionalmente) control de velocidad de la banda principal.

Orquestador Principal (main_sistema_banda.py):

Desarrollo de la lógica principal que integra la captura de imágenes (activada por el sensor de disparo), la llamada al módulo de IA para clasificación, y la crucial lógica de sincronización para activar el motor_driver_interface.py en el momento exacto en que el objeto clasificado llega al desviador correspondiente. Este cálculo considerará la velocidad de la banda y la distancia cámara-desviador.

Implementación de la gestión de la cola de objetos (object_queue) y el manejo de hilos (threading) para procesar múltiples objetos en la banda.

Módulo de Comunicación (Comunicacion/rpi_plc_interface.py): Si se opta por una arquitectura híbrida con un PLC (ej: Siemens LOGO!), se desarrollará la comunicación (ej: Modbus TCP) entre la Raspberry Pi y el PLC.

Interfaz de Usuario (InterfazUsuario_Monitoreo): Desarrollo de la aplicación web (Flask backend, React/Vite frontend) para visualización y monitoreo.
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

# Agradecimientos

Deseamos expresar nuestro más sincero agradecimiento a todas aquellas personas e instituciones que, de una u otra forma, contribuyeron al desarrollo y culminación de este proyecto de tesis. Su apoyo ha sido fundamental en cada etapa de esta investigación.

En primer lugar, extendemos un especial agradecimiento a nuestro asesor de tesis, Ing. Melquisidec Pérez Ramírez, por su invaluable guía, paciencia y sabios consejos a lo largo de todo este proceso. Su experiencia y disposición para resolver nuestras dudas fueron cruciales para superar los desafíos encontrados y para orientar nuestro trabajo hacia los objetivos propuestos.

Agradecemos a la Colegio Español Padre Arrupe por brindarnos la formación académica y los recursos necesarios que sentaron las bases para la realización de este proyecto. Asimismo, a los docentes de Electronica III, quienes compartieron sus conocimientos y nos motivaron a explorar el fascinante campo de la inteligencia artificial y la automatización industrial.

Un reconocimiento especial a nuestros compañeros de equipo, por su dedicación, esfuerzo conjunto y el excelente ambiente de colaboración que mantuvimos durante el desarrollo de este proyecto. Las largas horas de trabajo, las discusiones constructivas y el apoyo mutuo fueron esenciales para alcanzar nuestras metas.

A nuestras familias, por su comprensión, amor incondicional y constante aliento, especialmente en los momentos de mayor exigencia. Su fe en nosotros fue una fuente de motivación invaluable.

A nuestros amigos y compañeros de clase, por su camaradería, por compartir ideas y por el apoyo moral ofrecido durante este retador pero gratificante camino.

Finalmente, agradecemos a cualquier otra persona que, aunque no haya sido mencionada explícitamente, haya aportado de alguna manera al desarrollo de esta tesis.

Este logro es el resultado del esfuerzo y la colaboración de muchas personas, y a todas ellas, les dedicamos este trabajo.

¡Muchas gracias!

Cristian Hernández
Gabriel Calderón
Elías Bautista


## Autores

*   Gabriel Calderón
*   Elias Bautista
*   Cristian Hernandez

## Licencia

<<<<<<< HEAD
Este proyecto está licenciado bajo la Licencia MIT.

Copyright (c) 2025 Gabriel Calderón, Elias Bautista, Cristian Hernandez.

Se concede permiso, de forma gratuita, a cualquier persona que obtenga una copia de este software y de los archivos de documentación asociados (el "Software"), para tratar el Software sin restricciones, incluyendo, sin limitación, los derechos de uso, copia, modificación, fusión, publicación, distribución, sublicencia y/o venta de copias del Software, y para permitir a las personas a las que se les proporcione el Software hacerlo, sujeto a las siguientes condiciones:

El aviso de copyright anterior y este aviso de permiso se incluirán en todas las copias o partes sustanciales del Software.

EL SOFTWARE SE PROPORCIONA "TAL CUAL", SIN GARANTÍA DE NINGÚN TIPO, EXPRESA O IMPLÍCITA, INCLUYENDO PERO NO LIMITADO A GARANTÍAS DE COMERCIABILIDAD, IDONEIDAD PARA UN PROPÓSITO PARTICULAR Y NO INFRACCIÓN. EN NINGÚN CASO LOS AUTORES O TITULARES DEL COPYRIGHT SERÁN RESPONSABLES DE NINGUNA RECLAMACIÓN, DAÑO U OTRA RESPONSABILIDAD, YA SEA EN UNA ACCIÓN DE CONTRATO, AGRAVIO O DE OTRO MODO, DERIVADA DE, FUERA DE O EN CONEXIÓN CON EL SOFTWARE O EL USO U OTRAS OPERACIONES EN EL SOFTWARE.
=======
MIT

>>>>>>> 475d6d47aef12bc703f8be2ceaff437b6368fd8e

---
*Junio de 2025* 
