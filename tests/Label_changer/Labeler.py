# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# relabel_dataset_enhanced.py - Utilidad Avanzada para Re-etiquetado de Datasets
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez.
# Fecha: Junio 2025
# Versión: 2.1 Enhanced Edition
#
# Descripción:
#   Herramienta de línea de comandos para re-etiquetar datasets de detección
#   de objetos en formato YOLO (.txt). Ofrece logging, backups automáticos,
#   filtrado de clases y una barra de progreso.
# -----------------------------------------------------------------------------

import os
import argparse
import logging
import shutil
from pathlib import Path

class DatasetRelabeler:
    """
    Gestiona el proceso de re-etiquetado de un dataset de forma segura y eficiente.
    """

    def __init__(self, labels_path, new_class_id, target_classes, backup=True):
        self.labels_path = Path(labels_path)
        self.new_class_id = new_class_id
        self.target_classes = set(target_classes)
        self.do_backup = backup
        self.processed_files = 0
        self.modified_files = 0
        self.ignored_files = 0

        # Configurar logging para guardar en la carpeta de destino
        log_file = self.labels_path.parent / 'relabel.log'
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file, mode='w'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def _create_backup(self):
        """Crea una copia de seguridad de la carpeta de etiquetas."""
        backup_path = self.labels_path.with_name(f"{self.labels_path.name}_backup_{int(time.time())}")
        try:
            shutil.copytree(self.labels_path, backup_path)
            self.logger.info(f"Respaldo creado exitosamente en: {backup_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error al crear el respaldo: {e}")
            return False

    def _should_process_file(self, file_path):
        """
        Determina si un archivo debe ser procesado.
        Solo procesa si contiene al menos una de las clases objetivo.
        """
        try:
            if file_path.stat().st_size == 0:
                return False # Ignorar archivos vacíos
            
            with open(file_path, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if parts:
                        class_id = int(parts[0])
                        if class_id in self.target_classes:
                            return True
            return False # No se encontraron clases objetivo
        except Exception as e:
            self.logger.warning(f"No se pudo leer {file_path.name} para verificación: {e}")
            return False

    def _process_single_file(self, file_path):
        """Procesa y re-etiqueta un único archivo de anotación."""
        new_lines = []
        modified = False
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()

            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 5:
                    try:
                        class_id = int(parts[0])
                        # Si la clase está en las que queremos cambiar, la reemplazamos.
                        # Si no, la dejamos como está.
                        if class_id in self.target_classes:
                            new_line = f"{self.new_class_id} {' '.join(parts[1:])}"
                            new_lines.append(new_line)
                            modified = True
                        else:
                            new_lines.append(line.strip()) # Mantener línea original
                    except ValueError:
                        self.logger.warning(f"Línea inválida en {file_path.name}: {line.strip()}")
                        new_lines.append(line.strip())
                else:
                    # Conservar líneas que no son anotaciones válidas si es necesario
                    new_lines.append(line.strip())

            if modified:
                with open(file_path, 'w') as f:
                    # Escribir solo si hubo cambios
                    f.write('\n'.join(new_lines) + '\n')
                self.modified_files += 1
            else:
                self.ignored_files += 1

        except Exception as e:
            self.logger.error(f"Error procesando {file_path.name}: {e}")
            self.ignored_files += 1

    @staticmethod
    def _print_progress_bar(iteration, total, prefix='', suffix='', length=50, fill='█'):
        """Imprime una barra de progreso en la consola."""
        percent = ("{0:.1f}").format(100 * (iteration / float(total)))
        filled_length = int(length * iteration // total)
        bar = fill * filled_length + '-' * (length - filled_length)
        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
        if iteration == total:
            print()

    def run(self):
        """Ejecuta el proceso completo de re-etiquetado."""
        if not self.labels_path.is_dir():
            self.logger.error(f"Error: La ruta no existe o no es una carpeta -> {self.labels_path}")
            return

        self.logger.info("--- Iniciando Proceso de Re-etiquetado v2.1 ---")
        self.logger.info(f"Carpeta de destino: {self.labels_path}")
        self.logger.info(f"Clases a modificar: {sorted(list(self.target_classes))}")
        self.logger.info(f"Nuevo ID de clase: {self.new_class_id}")
        
        if self.do_backup:
            if not self._create_backup():
                if input("No se pudo crear el respaldo. ¿Desea continuar de todos modos? (s/n): ").lower() != 's':
                    self.logger.warning("Proceso cancelado por el usuario.")
                    return
        
        # Primero, filtramos los archivos que necesitan ser procesados
        all_files = [f for f in self.labels_path.glob('*.txt')]
        files_to_process = [f for f in all_files if self._should_process_file(f)]
        self.ignored_files = len(all_files) - len(files_to_process)
        total_files = len(files_to_process)
        
        self.logger.info(f"Se encontraron {len(all_files)} archivos .txt. De ellos, {total_files} serán procesados.")
        
        if not files_to_process:
            self.logger.info("No se encontraron archivos que requieran modificación.")
            self.logger.info("--- Proceso Finalizado ---")
            return
            
        # Procesar los archivos filtrados
        for i, file_path in enumerate(files_to_process):
            self._process_single_file(file_path)
            self.processed_files += 1
            self._print_progress_bar(i + 1, total_files, prefix='Progreso:', suffix='Completado')

        self.logger.info("\n--- Proceso Finalizado ---")
        self.logger.info(f"Resumen:")
        self.logger.info(f"  - Archivos procesados: {self.processed_files}")
        self.logger.info(f"  - Archivos modificados: {self.modified_files}")
        self.logger.info(f"  - Archivos ignorados (vacíos o sin clases objetivo): {self.ignored_files}")
        self.logger.info(f"Para más detalles, revisa el archivo 'relabel.log' en la carpeta superior.")

def main():
    """Punto de entrada principal para la ejecución desde la línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Herramienta Avanzada para Re-etiquetar Datasets v2.1",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "labels_path",
        type=str,
        help="Ruta a la carpeta que contiene los archivos de etiquetas .txt."
    )
    parser.add_argument(
        "--new-id",
        type=int,
        required=True,
        help="El nuevo ID de clase que se asignará."
    )
    parser.add_argument(
        "--target-classes",
        type=int,
        nargs='+',
        required=True,
        help="Lista de IDs de clase que serán reemplazados (ej: --target-classes 0 1 2 3)."
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Opcional: Si se especifica, no se creará una copia de seguridad."
    )
    
    args = parser.parse_args()
    
    relabeler = DatasetRelabeler(
        labels_path=args.labels_path,
        new_class_id=args.new_id,
        target_classes=args.target_classes,
        backup=not args.no_backup
    )
    relabeler.run()

if __name__ == '__main__':
    import time # Necesario para el timestamp del backup
    main()