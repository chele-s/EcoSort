# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Trash_detect.py - Script para Detección de Residuos con YOLO
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción: Utiliza un modelo YOLO entrenado para detectar tipos de
#              residuos (Metal, Vidrio, Plástico, Cartón) utilizando
#              la cámara en tiempo real. Incluye la clase TrashDetector.
# -----------------------------------------------------------------------------

import os
import sys
import cv2
import math
import argparse
import yaml
import logging
import time
from pathlib import Path
from ultralytics import YOLO

# Configurar logging básico
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('TrashDetect')

# Valores por defecto
DEFAULT_MODEL_PATH = 'models/best.pt'
DEFAULT_CAMERA_INDEX = 0
DEFAULT_CAMERA_WIDTH = 1280
DEFAULT_CAMERA_HEIGHT = 720
DEFAULT_CONFIDENCE = 0.45
DEFAULT_DATA_YAML = '../dataset_basura/data.yaml'


class TrashDetector:
    """
    Clase para encapsular la detección de objetos con un modelo YOLO.
    """
    def __init__(self, model_path: str, min_confidence: float = 0.5):
        """
        Inicializa el detector de basura.

        Args:
            model_path (str): Ruta al archivo del modelo YOLO (ej: 'best.pt').
            min_confidence (float): Umbral mínimo de confianza para las detecciones.
        """
        self.model_path = model_path
        self.min_confidence = min_confidence
        
        if not os.path.exists(self.model_path):
            logger.error(f"Modelo IA no encontrado en la ruta: {self.model_path}")
            raise FileNotFoundError(f"Modelo IA no encontrado en {self.model_path}")
        
        try:
            logger.info(f"Cargando modelo IA desde {self.model_path}...")
            self.model = YOLO(self.model_path)
            # class_names are part of the model itself after training
            self.model_class_names = self.model.names
            logger.info(f"Modelo IA cargado. Clases detectables por el modelo: {self.model_class_names}")
        except Exception as e:
            logger.error(f"Error crítico al cargar el modelo YOLO desde '{self.model_path}': {e}", exc_info=True)
            raise e

    def detect_objects(self, frame: any) -> list:
        """
        Detecta objetos en un frame dado.

        Args:
            frame: El frame de imagen (formato OpenCV/numpy array).

        Returns:
            list: Una lista de tuplas, donde cada tupla contiene:
                  (nombre_clase_detectada, confianza, (x1, y1, x2, y2)).
                  Retorna una lista vacía si no hay detecciones válidas.
        """
        detections_output = []
        if frame is None:
            logger.warning("Frame de entrada para detect_objects es None.")
            return detections_output

        try:
            # Realizar inferencia con el umbral de confianza especificado
            results = self.model(frame, verbose=False, conf=self.min_confidence) 
            
            # Asumiendo que 'results' es una lista de objetos Results
            for res in results: 
                boxes = res.boxes # Acceder al atributo 'boxes'
                for box in boxes:
                    conf = float(box.conf[0])
                    # La confianza ya está filtrada por self.model(..., conf=self.min_confidence)
                    # No es necesario un segundo filtro aquí a menos que se desee lógica adicional
                        
                    cls_idx = int(box.cls[0])
                    
                    if cls_idx < 0 or cls_idx >= len(self.model_class_names):
                        logger.warning(f"Índice de clase ({cls_idx}) fuera de rango para las clases del modelo ({len(self.model_class_names)}). Detección ignorada.")
                        continue
                    
                    detected_class_name = self.model_class_names[cls_idx] 
                                        
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    
                    # Asegurar que las coordenadas estén dentro de los límites del frame
                    h, w = frame.shape[:2]
                    x1_c = max(0, min(x1, w - 1))
                    y1_c = max(0, min(y1, h - 1))
                    x2_c = max(0, min(x2, w - 1))
                    y2_c = max(0, min(y2, h - 1))
                    
                    # Solo añadir si las coordenadas forman una caja válida
                    if x1_c < x2_c and y1_c < y2_c:
                        detections_output.append((detected_class_name, conf, (x1_c, y1_c, x2_c, y2_c)))
                    else:
                        logger.debug(f"Caja inválida después del recorte: ({x1_c},{y1_c})-({x2_c},{y2_c}) para {detected_class_name}")
            
        except Exception as e:
            logger.error(f"Error durante la detección de objetos: {e}", exc_info=True)
        
        return detections_output


def parse_arguments():
    """
    Parsea los argumentos de línea de comandos para configurar la detección.
    """
    parser = argparse.ArgumentParser(description='Detección de residuos en tiempo real con YOLOv8')
    
    parser.add_argument('--model', type=str, default=DEFAULT_MODEL_PATH,
                        help=f'Ruta al modelo YOLOv8 (default: {DEFAULT_MODEL_PATH})')
    parser.add_argument('--camera', type=int, default=DEFAULT_CAMERA_INDEX,
                        help=f'Índice de la cámara a usar (default: {DEFAULT_CAMERA_INDEX})')
    parser.add_argument('--width', type=int, default=DEFAULT_CAMERA_WIDTH,
                        help=f'Ancho de la captura de cámara (default: {DEFAULT_CAMERA_WIDTH})')
    parser.add_argument('--height', type=int, default=DEFAULT_CAMERA_HEIGHT,
                        help=f'Alto de la captura de cámara (default: {DEFAULT_CAMERA_HEIGHT})')
    parser.add_argument('--conf', type=float, default=DEFAULT_CONFIDENCE,
                        help=f'Umbral de confianza para detecciones (default: {DEFAULT_CONFIDENCE})')
    parser.add_argument('--data', type=str, default=DEFAULT_DATA_YAML,
                        help=f'Archivo data.yaml con nombres de clases (default: {DEFAULT_DATA_YAML})')
    
    return parser.parse_args()


def load_class_names_from_yaml(yaml_path: str) -> list:
    """
    Carga los nombres de clases desde el archivo data.yaml.
    Si no puede cargar el archivo, devuelve una lista predeterminada.
    """
    default_classes = ['Metal', 'Glass', 'Plastic', 'Carton']
    
    if not os.path.exists(yaml_path):
        logger.warning(f"Archivo {yaml_path} no encontrado. Usando nombres de clases por defecto.")
        return default_classes
    
    try:
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
            if 'names' in data and isinstance(data['names'], list):
                logger.info(f"Clases cargadas de {yaml_path}: {data['names']}")
                return data['names']
            else:
                logger.warning(f"Formato incorrecto en {yaml_path}. Usando nombres de clases por defecto.")
                return default_classes
    except Exception as e:
        logger.error(f"Error al cargar {yaml_path}: {e}")
        return default_classes


def setup_camera(camera_index, width, height):
    """
    Configura la cámara con los parámetros especificados.
    Devuelve el objeto de captura o None si falla.
    """
    try:
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.error(f"No se pudo abrir la cámara con índice {camera_index}")
            return None
        
        # Establecer resolución (puede no funcionar en todas las cámaras)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        
        # Verificar la resolución real (puede diferir de la solicitada)
        actual_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        logger.info(f"Cámara inicializada. Resolución: {actual_width}x{actual_height}")
        
        return cap
    
    except Exception as e:
        logger.error(f"Error al configurar la cámara: {e}")
        return None


def calculate_fps(start_time, frame_count):
    """
    Calcula los FPS basado en el tiempo transcurrido y el número de frames.
    """
    elapsed_time = time.time() - start_time
    if elapsed_time > 0:
        return frame_count / elapsed_time
    return 0


def main():
    """Función principal del programa para prueba standalone."""
    args = parse_arguments()
    
    # Cargar nombres de clases desde data.yaml (para visualización)
    # La clase TrashDetector usará los nombres internos del modelo.
    display_class_names = load_class_names_from_yaml(args.data) 
    
    # Inicializar el detector
    try:
        # Nota: TrashDetector ahora solo toma model_path y min_confidence.
        # class_names son internos del modelo.
        detector = TrashDetector(model_path=args.model, min_confidence=args.conf)
    except Exception as e:
        logger.critical(f"No se pudo inicializar TrashDetector: {e}")
        return 1
    
    cap = setup_camera(args.camera, args.width, args.height)
    if cap is None:
        return 1
    
    start_time = time.time()
    frame_count = 0
    fps = 0
    
    window_name = "EcoSort - AI Waste Detection Test"
    cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
    
    logger.info("Iniciando bucle de detección para prueba. Presiona 'ESC' o 'q' para salir.")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                logger.error("Error al capturar frame. Comprueba la conexión de la cámara.")
                time.sleep(1.0)
                cap = setup_camera(args.camera, args.width, args.height)
                if cap is None: break
                continue
            
            # Realizar detección usando la clase TrashDetector
            detections = detector.detect_objects(frame)
            annotated_frame = frame.copy()

            # Anotar el frame con las detecciones
            for cls_name, conf, box_coords in detections:
                x1, y1, x2, y2 = box_coords
                
                # Determinar color (opcional, basado en display_class_names si se quiere consistencia)
                color = (0, 255, 0) # Verde por defecto
                # Example: try: color_idx = display_class_names.index(cls_name) % len(colors_list) catch: pass
                
                cv2.rectangle(annotated_frame, (x1, y1), (x2, y2), color, 2)
                label_text = f'{cls_name} {conf:.2f}'
                
                # Dibujar fondo para el texto
                (text_width, text_height), baseline = cv2.getTextSize(label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.rectangle(annotated_frame, (x1, y1 - text_height - baseline), (x1 + text_width, y1), color, -1)
                cv2.putText(annotated_frame, label_text, (x1, y1 - baseline), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,0), 2)

            frame_count += 1
            if frame_count >= 5: # Calcular FPS cada 5 frames
                fps = calculate_fps(start_time, frame_count)
                start_time = time.time()
                frame_count = 0
            
            cv2.putText(annotated_frame, f"FPS: {fps:.1f}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            cv2.imshow(window_name, annotated_frame)
            
            key = cv2.waitKey(1)
            if key == 27 or key == ord('q'):
                logger.info("Saliendo por petición del usuario.")
                break
    
    except KeyboardInterrupt:
        logger.info("Interrupción por teclado (Ctrl+C). Saliendo...")
    except Exception as e:
        logger.error(f"Error inesperado en el bucle principal de prueba: {e}", exc_info=True)
    finally:
        if cap is not None:
            cap.release()
        cv2.destroyAllWindows()
        logger.info("Recursos liberados. Prueba finalizada.")
    
    return 0


if __name__ == "__main__":
    # Ajustar rutas por defecto si se ejecuta standalone desde IA_Clasificacion
    # Esto es un poco hacky; idealmente, las rutas se manejan de forma más robusta
    # o el script asume que se ejecuta desde la raíz del proyecto.
    if os.path.basename(os.getcwd()) == "IA_Clasificacion":
        DEFAULT_MODEL_PATH = 'models/best.pt'
        DEFAULT_DATA_YAML = 'dataset_basura/data.yaml'
        logger.info(f"Script ejecutado desde IA_Clasificacion. Rutas ajustadas: Model='{DEFAULT_MODEL_PATH}', YAML='{DEFAULT_DATA_YAML}'")
    else: # Asumir ejecución desde raíz del proyecto
        DEFAULT_MODEL_PATH = 'IA_Clasificacion/models/best.pt'
        DEFAULT_DATA_YAML = 'IA_Clasificacion/dataset_basura/data.yaml'
        logger.info(f"Script ejecutado desde raíz (o desconocido). Rutas: Model='{DEFAULT_MODEL_PATH}', YAML='{DEFAULT_DATA_YAML}'")

    sys.exit(main())