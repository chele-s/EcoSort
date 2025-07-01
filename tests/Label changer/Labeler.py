import os

def relabel_dataset(labels_path, new_class_id):
    """
    Recorre todos los archivos .txt en una carpeta y cambia el ID de la clase.
    
    Args:
        labels_path (str): Ruta a la carpeta de etiquetas (e.g., 'dataset_combinado/labels/train').
        new_class_id (int): El nuevo ID de clase para todas las anotaciones.
    """
    if not os.path.exists(labels_path):
        print(f"Error: La ruta no existe -> {labels_path}")
        return

    print(f"Procesando etiquetas en: {labels_path}")
    for filename in os.listdir(labels_path):
        if filename.endswith(".txt"):
            file_path = os.path.join(labels_path, filename)
            new_lines = []
            try:
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                for line in lines:
                    parts = line.strip().split()
                    if len(parts) >= 5:
                        # La estructura es: class_id x_center y_center width height
                        # Cambiamos solo el class_id
                        new_line = f"{new_class_id} {' '.join(parts[1:])}"
                        new_lines.append(new_line)
                
                with open(file_path, 'w') as f:
                    f.write('\n'.join(new_lines) + '\n')
                    
            except Exception as e:
                print(f"Error procesando {filename}: {e}")
    print("¡Etiquetas actualizadas!")

OTHER_CLASS_ID = 3
