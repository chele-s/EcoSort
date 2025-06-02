# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# rpi_plc_interface.py - Módulo para comunicación con PLC industrial
#
# Autor(es): Gabriel Calderón, Elias Bautista, Cristian Hernandez
# Fecha: Junio de 2025
# Descripción:
#   Este módulo maneja la comunicación entre la Raspberry Pi y el PLC
#   usando protocolo Modbus TCP/IP para controlar los actuadores de división
#   y monitorear el estado del sistema.
# -----------------------------------------------------------------------------

import logging
import time
import json
import threading
from typing import Optional, Dict, List, Tuple
from pymodbus.client import ModbusTcpClient
from pymodbus.exceptions import ModbusException, ConnectionException
from queue import Queue, Empty

logger = logging.getLogger(__name__)

class PLCInterface:
    """
    Interfaz para comunicación con PLC industrial mediante Modbus TCP.
    Maneja la activación de actuadores y lectura de estados.
    """
    
    def __init__(self, plc_ip: str, plc_port: int = 502, unit_id: int = 1):
        """
        Inicializa la interfaz del PLC.
        
        Args:
            plc_ip: Dirección IP del PLC
            plc_port: Puerto Modbus (por defecto 502)
            unit_id: ID de la unidad Modbus (por defecto 1)
        """
        self.plc_ip = plc_ip
        self.plc_port = plc_port
        self.unit_id = unit_id
        self.client = None
        self.connected = False
        
        # Mapeo de registros Modbus (genéricos y de control de banda)
        # Los registros específicos de actuadores de desviación se pasarán directamente
        # a activate_diverter.
        self.register_map = {
            # Registros de control (Coils - escritura)
            'banda_start': 10,        # Coil 10
            'banda_stop': 11,         # Coil 11
            'emergency_stop': 20,     # Coil 20
            
            # Registros de estado (Input Registers - lectura)
            'plc_status': 0,          # Register 0 (ej: estado general, heartbeat)
            'actuator_status_general': 1, # Register 1 (ej: bitmap de todos los actuadores, si el PLC lo provee)
            'banda_speed_actual': 2,  # Register 2 (velocidad actual leída del PLC)
            'error_code': 3,          # Register 3 (código de error general del PLC)
            'product_count_plc': 4,   # Register 4 (si el PLC lleva un conteo)
            
            # Registros de configuración (Holding Registers - lectura/escritura)
            'diverter_activation_time_ms_hr': 10,  # Holding Register 10 (tiempo que el PLC mantiene activo un desviador)
            'plc_delay_time_ms_hr': 11,            # Holding Register 11 (un delay general configurable en PLC)
            'banda_speed_setpoint_hr': 12          # Holding Register 12 (setpoint de velocidad para la banda)
        }
        
        self.command_queue = Queue()
        self.worker_thread = None
        self.running = False
        
        self.stats = {
            'commands_sent': 0,
            'commands_failed': 0,
            'reconnection_attempts': 0,
            'last_error': None
        }
        
    def connect(self) -> bool:
        """Establece conexión con el PLC."""
        try:
            if self.client:
                try:
                    self.client.close()
                except Exception:
                    pass # Ignore errors during close if already disconnected
                
            logger.info(f"Conectando a PLC en {self.plc_ip}:{self.plc_port}")
            self.client = ModbusTcpClient(
                host=self.plc_ip,
                port=self.plc_port,
                timeout=3,      # Tiempo de espera para una respuesta
                retries=2,      # Número de reintentos en caso de fallo de comunicación
                retry_on_empty=True # Reintentar si la respuesta está vacía
            )
            
            if self.client.connect():
                self.connected = True
                logger.info("Conexión con PLC establecida exitosamente")
                
                if self.worker_thread is None or not self.worker_thread.is_alive():
                    self.running = True
                    self.worker_thread = threading.Thread(target=self._process_commands)
                    self.worker_thread.daemon = True
                    self.worker_thread.start()
                
                return True
            else:
                logger.error("No se pudo conectar al PLC después de reintentos.")
                self.connected = False
                return False
                
        except Exception as e:
            logger.error(f"Excepción al conectar/crear cliente PLC: {e}")
            self.connected = False
            self.stats['last_error'] = str(e)
            return False
    
    def disconnect(self):
        """Cierra la conexión con el PLC."""
        self.running = False
        if self.worker_thread and self.worker_thread.is_alive():
            try:
                self.worker_thread.join(timeout=1.0) # Dar tiempo al worker para terminar
            except RuntimeError:
                pass # Si el hilo no ha arrancado
            
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass # Ignorar errores al cerrar si ya está cerrado o hubo problemas
            self.connected = False
            logger.info("Desconectado del PLC")
    
    def _reconnect(self):
        """Intenta reconectar al PLC."""
        if not self.running: # No reconectar si se está desconectando
            return False
        logger.info("PLC desconectado. Intentando reconectar...")
        self.connected = False # Marcar como desconectado
        self.stats['reconnection_attempts'] += 1
        time.sleep(2)  # Espera antes de reconectar
        return self.connect()
    
    def _process_commands(self):
        """Thread worker para procesar comandos de forma asíncrona."""
        while self.running:
            try:
                command = self.command_queue.get(timeout=0.2)
                
                if not self.connected:
                    logger.warning(f"PLC no conectado. Intentando reconectar antes de procesar comando: {command.get('type')}")
                    if not self._reconnect():
                        logger.error(f"Fallo al reconectar. Comando {command.get('type')} no procesado.")
                        self.stats['commands_failed'] += 1
                        self.command_queue.task_done()
                        continue # Ir al siguiente ciclo del while

                # Procesar comando
                success = False
                if command['type'] == 'activate_diverter':
                    success = self._execute_diverter_activation(
                        command['coil_address'],
                        command['duration_ms']
                    )
                elif command['type'] == 'set_banda_speed':
                    success = self._execute_set_banda_speed(command['speed_percent'])
                elif command['type'] == 'emergency_stop':
                    success = self._execute_emergency_stop()
                
                if success:
                    self.stats['commands_sent'] += 1
                else:
                    self.stats['commands_failed'] += 1
                    
                self.command_queue.task_done()
                
            except Empty:
                # No hay comandos, verificar conexión si es necesario o simplemente continuar
                if self.client and not self.connected and self.running: # Si debe estar corriendo pero no está conectado
                    self._reconnect()
                continue
            except Exception as e:
                logger.error(f"Error procesando comando en worker: {e}", exc_info=True)
                self.stats['commands_failed'] += 1
                # Considerar si se debe re-encolar el comando o marcarlo como fallido.
                # Por ahora, se asume que task_done se llamará si la excepción no es Empty.
                if self.command_queue.unfinished_tasks > 0 :
                     self.command_queue.task_done() # Asegurar que task_done se llame

    def activate_diverter(self, coil_address: int, duration_ms: int) -> bool:
        """
        Encola un comando para activar un actuador de división específico.
        
        Args:
            coil_address: Dirección del coil Modbus para el actuador.
            duration_ms: Duración de activación en milisegundos.
        Return:
            bool: True si el comando fue encolado (no implica ejecución exitosa aún).
        """
        if not isinstance(coil_address, int) or coil_address < 0:
            logger.error(f"Dirección de coil inválida: {coil_address}")
            return False
            
        command = {
            'type': 'activate_diverter',
            'coil_address': coil_address,
            'duration_ms': duration_ms,
            'timestamp': time.time()
        }
        
        self.command_queue.put(command)
        logger.info(f"Comando de activación encolado para coil {coil_address} por {duration_ms}ms")
        return True # Devuelve True porque el comando fue encolado
    
    def _execute_diverter_activation(self, coil_address: int, duration_ms: int) -> bool:
        """Ejecuta la activación del actuador (coil) en el PLC."""
        if not self.connected: # Doble chequeo, aunque el worker también lo hace
            logger.error(f"No conectado al PLC. No se puede activar coil {coil_address}.")
            return False
                
        try:
            # 1. Configurar tiempo de activación en el Holding Register correspondiente
            # Asumimos que el PLC usará este valor para temporizar la desactivación del coil.
            hr_address = self.register_map.get('diverter_activation_time_ms_hr')
            if hr_address is None:
                logger.error("Holding Register 'diverter_activation_time_ms_hr' no definido en register_map.")
                return False

            result_hr = self.client.write_register(
                hr_address,
                duration_ms,
                unit=self.unit_id
            )
            
            if result_hr.isError():
                logger.error(f"Error Modbus configurando tiempo de activación ({duration_ms}ms) en HR {hr_address} para coil {coil_address}: {result_hr}")
                self.stats['last_error'] = str(result_hr)
                self.connected = False # Asumir desconexión en error Modbus
                return False

            # 2. Activar el coil del actuador
            result_coil = self.client.write_coil(
                coil_address,
                True, # Activar
                unit=self.unit_id
            )
            
            if not result_coil.isError():
                logger.info(f"Coil {coil_address} activado. PLC gestionará desactivación tras {duration_ms}ms.")
                return True
            else:
                logger.error(f"Error Modbus activando coil {coil_address}: {result_coil}")
                self.stats['last_error'] = str(result_coil)
                self.connected = False
                return False
                
        except ModbusException as e: # Captura ConnectionException también
            logger.error(f"Excepción Modbus activando coil {coil_address}: {e}")
            self.connected = False
            self.stats['last_error'] = str(e)
            return False
        except Exception as e: # Otras excepciones inesperadas
            logger.error(f"Excepción inesperada activando coil {coil_address}: {e}", exc_info=True)
            self.connected = False # Mejor asumir desconexión
            self.stats['last_error'] = str(e)
            return False
    
    def start_banda(self, speed_percent: int = 75):
        """
        Encola un comando para iniciar la banda transportadora.
        
        Args:
            speed_percent: Velocidad en porcentaje (0-100)
        """
        command = {
            'type': 'set_banda_speed',
            'speed_percent': speed_percent
        }
        self.command_queue.put(command)
        logger.info(f"Comando de inicio/ajuste de velocidad de banda encolado ({speed_percent}%).")
    
    def stop_banda(self):
        """Encola un comando para detener la banda transportadora."""
        # Detener la banda es equivalente a poner su velocidad a 0
        command = {
            'type': 'set_banda_speed',
            'speed_percent': 0 
        }
        self.command_queue.put(command)
        logger.info("Comando de parada de banda encolado.")
    
    def _execute_set_banda_speed(self, speed_percent: int) -> bool:
        """Ejecuta el comando de velocidad de banda en el PLC."""
        if not self.connected:
            logger.error(f"No conectado al PLC. No se puede ajustar velocidad de banda a {speed_percent}%.")
            return False
                
        try:
            speed_val = max(0, min(100, speed_percent)) # Asegurar que esté en rango 0-100
            
            # 1. Escribir el setpoint de velocidad en el Holding Register
            hr_speed_setpoint = self.register_map.get('banda_speed_setpoint_hr')
            if hr_speed_setpoint is None:
                logger.error("HR 'banda_speed_setpoint_hr' no definido en register_map.")
                return False
            
            result_hr = self.client.write_register(
                hr_speed_setpoint,
                speed_val,
                unit=self.unit_id
            )
            if result_hr.isError():
                logger.error(f"Error Modbus configurando velocidad ({speed_val}%) en HR {hr_speed_setpoint}: {result_hr}")
                self.stats['last_error'] = str(result_hr)
                self.connected = False
                return False

            # 2. Enviar comando de Start o Stop basado en la velocidad
            # Asumimos que el PLC usa el setpoint de HR y estos coils para actuar.
            coil_to_trigger = self.register_map['banda_start'] if speed_val > 0 else self.register_map['banda_stop']
            
            result_coil = self.client.write_coil(
                coil_to_trigger,
                True, # Activar el coil (Start o Stop)
                unit=self.unit_id
            )
            # El PLC debería auto-resetear este coil si es un pulso, o actuar según su lógica.

            if not result_coil.isError():
                action = "iniciada/ajustada a" if speed_val > 0 else "detenida (velocidad 0%)"
                logger.info(f"Banda {action} {speed_val}%. Coil {coil_to_trigger} activado.")
                return True
            else:
                logger.error(f"Error Modbus activando coil {coil_to_trigger} para banda: {result_coil}")
                self.stats['last_error'] = str(result_coil)
                self.connected = False
                return False
                
        except ModbusException as e:
            logger.error(f"Excepción Modbus ajustando velocidad de banda: {e}")
            self.connected = False
            self.stats['last_error'] = str(e)
            return False
        except Exception as e:
            logger.error(f"Excepción inesperada ajustando velocidad de banda: {e}", exc_info=True)
            self.connected = False
            self.stats['last_error'] = str(e)
            return False
    
    def emergency_stop(self):
        """Encola la activación de la parada de emergencia."""
        command = {'type': 'emergency_stop', 'timestamp': time.time()}
        # La parada de emergencia podría necesitar saltar la cola o tener alta prioridad.
        # Por simplicidad, la añadimos a la misma cola, pero podría tener una cola dedicada.
        self.command_queue.put(command)
        logger.warning("¡PARADA DE EMERGENCIA encolada!")
    
    def _execute_emergency_stop(self) -> bool:
        """Ejecuta la parada de emergencia en el PLC."""
        # Este comando es crítico y debería intentar ejecutarse incluso si el cliente no está marcado como "connected",
        # ya que la conexión podría haberse perdido justo antes. El ModbusTcpClient intentará conectar si no lo está.
        if not self.client:
             logger.error("Cliente PLC no inicializado. No se puede ejecutar parada de emergencia.")
             return False
        try:
            coil_emerg = self.register_map.get('emergency_stop')
            if coil_emerg is None:
                logger.error("Coil 'emergency_stop' no definido en register_map.")
                return False

            logger.critical(f"Intentando activar coil de PARADA DE EMERGENCIA ({coil_emerg}) en PLC...")
            result = self.client.write_coil(
                coil_emerg,
                True, # Activar coil de emergencia
                unit=self.unit_id
            )
            if not result.isError():
                logger.critical(f"Coil de PARADA DE EMERGENCIA ({coil_emerg}) activado exitosamente en PLC.")
                self.connected = True # Si el comando pasó, estamos conectados.
                return True
            else:
                logger.error(f"Error Modbus activando coil de PARADA DE EMERGENCIA ({coil_emerg}): {result}")
                self.stats['last_error'] = str(result)
                # No necesariamente marcar como desconectado aquí, el reintento de conexión se hará
                # en el siguiente ciclo del worker o comando. El intento de emergencia es prioritario.
                # self.connected = False # Podría ser demasiado agresivo
                return False
        except Exception as e:
            logger.error(f"Excepción durante ejecución de parada de emergencia: {e}", exc_info=True)
            self.stats['last_error'] = str(e)
            # self.connected = False
            return False
    
    def read_plc_status(self) -> Optional[Dict]:
        """
        Lee el estado actual del PLC.
        
        Returns:
            Dict con el estado o None si hay error
        """
        if not self.connected or not self.client:
            # logger.debug("No conectado al PLC o cliente no inicializado, no se puede leer estado.")
            return None
            
        try:
            # Leer un bloque de Input Registers que contienen varios estados
            # El count debe ser el número de registros a leer desde la dirección de inicio.
            # Ejemplo: si plc_status es 0 y queremos leer 5 registros (0,1,2,3,4)
            start_address = self.register_map.get('plc_status', 0)
            num_registers_to_read = 5 # Ajustar según lo que se necesite/defina en PLC
            
            result = self.client.read_input_registers(
                address=start_address,
                count=num_registers_to_read, 
                unit=self.unit_id
            )
            
            if not result.isError():
                regs = result.registers
                # Mapear los registros leídos a nombres significativos
                # Este mapeo depende de cómo el PLC organice sus datos de estado.
                status_data = {
                    'raw_registers': regs,
                    'timestamp': time.time(),
                    'plc_general_status': regs[0] if len(regs) > 0 else None, # Desde plc_status
                    'actuators_bitmap': regs[1] if len(regs) > 1 else None, # Desde actuator_status_general
                    'banda_current_speed': regs[2] if len(regs) > 2 else None, # Desde banda_speed_actual
                    'plc_error_code': regs[3] if len(regs) > 3 else None, # Desde error_code
                    'plc_product_counter': regs[4] if len(regs) > 4 else None # Desde product_count_plc
                    # Añadir más campos según los registros que se lean
                }
                # logger.debug(f"Estado PLC leído: {status_data}")
                return status_data
            else:
                logger.error(f"Error Modbus leyendo estado del PLC (desde IR {start_address}, count {num_registers_to_read}): {result}")
                self.stats['last_error'] = str(result)
                self.connected = False
                return None
                
        except ModbusException as e:
            logger.error(f"Excepción Modbus leyendo estado PLC: {e}")
            self.connected = False
            self.stats['last_error'] = str(e)
            return None
        except Exception as e:
            logger.error(f"Excepción inesperada leyendo estado PLC: {e}", exc_info=True)
            self.connected = False
            self.stats['last_error'] = str(e)
            return None
    
    def get_statistics(self) -> Dict:
        """Obtiene estadísticas de la comunicación."""
        return {
            'connected': self.connected,
            'plc_ip': self.plc_ip,
            'commands_sent': self.stats['commands_sent'],
            'commands_failed': self.stats['commands_failed'],
            'reconnection_attempts': self.stats['reconnection_attempts'],
            'last_error_message': self.stats['last_error'],
            'command_queue_size': self.command_queue.qsize()
        }
    
    def configure_plc_parameters(self, params: Dict[str, int]) -> bool:
        """
        Configura parámetros en Holding Registers del PLC.
        
        Args:
            params: Diccionario donde la clave es el nombre del parámetro 
                    (debe coincidir con claves en self.register_map que terminan en '_hr')
                    y el valor es el entero a escribir.
                    Ej: {'diverter_activation_time_ms_hr': 750, 'banda_speed_setpoint_hr': 80}
            
        Returns:
            True si todas las configuraciones fueron exitosas, False si alguna falló.
        """
        if not self.connected or not self.client:
            logger.error("No conectado al PLC. No se pueden configurar parámetros.")
            return False
        
        all_success = True
        for param_key, value_to_write in params.items():
            hr_address = self.register_map.get(param_key)
            if hr_address is None:
                logger.warning(f"Parámetro '{param_key}' no encontrado en el register_map del PLCInterface. Ignorando.")
                all_success = False # O continuar y marcar como no exitoso
                continue

            if not isinstance(value_to_write, int):
                logger.error(f"Valor para '{param_key}' debe ser un entero, se recibió {type(value_to_write)}. Configuración abortada para este parámetro.")
                all_success = False
                continue
            
            try:
                logger.info(f"Escribiendo en PLC HR {hr_address} (param: {param_key}) el valor: {value_to_write}")
                result = self.client.write_register(
                    hr_address,
                    value_to_write,
                    unit=self.unit_id
                )
                if result.isError():
                    logger.error(f"Error Modbus configurando HR {hr_address} ({param_key}) a {value_to_write}: {result}")
                    self.stats['last_error'] = str(result)
                    self.connected = False # Asumir desconexión en error
                    all_success = False
                    # break # Opcional: detenerse en el primer error
                else:
                    logger.info(f"Parámetro PLC '{param_key}' (HR {hr_address}) configurado a {value_to_write}.")

            except ModbusException as e:
                logger.error(f"Excepción Modbus configurando HR {hr_address} ({param_key}): {e}")
                self.connected = False
                self.stats['last_error'] = str(e)
                all_success = False
                # break
            except Exception as e:
                logger.error(f"Excepción inesperada configurando HR {hr_address} ({param_key}): {e}", exc_info=True)
                self.connected = False
                self.stats['last_error'] = str(e)
                all_success = False
                # break
        
        if all_success:
            logger.info("Todos los parámetros del PLC solicitados fueron configurados (o intentados).")
        else:
            logger.warning("Algunos parámetros del PLC no pudieron ser configurados.")
        return all_success

# Ejemplo de uso y prueba
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - [%(module)s.%(funcName)s:%(lineno)d] - %(message)s'
    )
    
    # Configurar IP del PLC (ajustar según tu configuración)
    PLC_IP_TEST = "192.168.1.100" # O "localhost" si usas un simulador Modbus
    PLC_PORT_TEST = 502
    
    # Crear instancia
    plc = PLCInterface(PLC_IP_TEST, PLC_PORT_TEST)
    
    if plc.connect():
        logger.info(f"Conectado al PLC ({PLC_IP_TEST}) exitosamente para prueba.")
        
        # Configurar parámetros (ejemplos)
        # Estos nombres deben existir en plc.register_map y terminar en '_hr'
        params_to_set = {
            'diverter_activation_time_ms_hr': 650, # Ejemplo: 650ms para la activación de desviadores
            'banda_speed_setpoint_hr': 70          # Ejemplo: 70% de velocidad para la banda
        }
        if plc.configure_plc_parameters(params_to_set):
            logger.info("Parámetros de prueba configurados en PLC.")
        else:
            logger.warning("Algunos parámetros de prueba no se pudieron configurar en PLC.")

        # Probar activación de actuadores (usando direcciones de coil directas)
        # Estas direcciones deben ser las correctas para tu PLC.
        COIL_METAL_TEST = 0  # Asumiendo que el coil para metal es 0
        COIL_PLASTIC_TEST = 1 # Asumiendo que el coil para plástico es 1
        
        logger.info(f"\n--- Probando actuador en coil {COIL_METAL_TEST} ---")
        if plc.activate_diverter(COIL_METAL_TEST, 500): # Activar por 500ms
            logger.info(f"Comando de activación para coil {COIL_METAL_TEST} encolado.")
        else:
            logger.error(f"Fallo al encolar comando para coil {COIL_METAL_TEST}")
        
        time.sleep(0.5) # Dar tiempo a que se procese el comando encolado

        logger.info(f"\n--- Probando actuador en coil {COIL_PLASTIC_TEST} ---")
        plc.activate_diverter(COIL_PLASTIC_TEST, 700) # Activar por 700ms
        
        # Esperar a que los comandos se procesen (la cola es asíncrona)
        # Para una prueba simple, podemos esperar un poco.
        # En una aplicación real, la lógica de la aplicación manejaría esto.
        logger.info("Esperando que se procesen los comandos encolados (aprox 2s)...")
        time.sleep(2) 

        # Leer estado
        logger.info("\n--- Leyendo estado del PLC ---")
        status = plc.read_plc_status()
        if status:
            logger.info(f"Estado del PLC: {json.dumps(status, indent=2)}")
        else:
            logger.warning("No se pudo leer el estado del PLC o está desconectado.")
        
        # Probar control de banda
        logger.info("\n--- Probando control de banda ---")
        logger.info("Iniciando banda al 50%...")
        plc.start_banda(speed_percent=50)
        time.sleep(2) # Esperar procesamiento

        status_after_banda_start = plc.read_plc_status()
        if status_after_banda_start:
             logger.info(f"Estado PLC post-arranque banda: {json.dumps(status_after_banda_start, indent=2)}")
        
        logger.info("Deteniendo banda...")
        plc.stop_banda()
        time.sleep(2) # Esperar procesamiento

        status_after_banda_stop = plc.read_plc_status()
        if status_after_banda_stop:
             logger.info(f"Estado PLC post-parada banda: {json.dumps(status_after_banda_stop, indent=2)}")

        # Mostrar estadísticas
        stats = plc.get_statistics()
        logger.info(f"\nEstadísticas de comunicación con PLC: {json.dumps(stats, indent=2)}")
        
        # Prueba de parada de emergencia
        logger.info("\n--- Probando Parada de Emergencia ---")
        plc.emergency_stop()
        time.sleep(1) # Dar tiempo a procesar
        stats_after_emerg = plc.get_statistics()
        logger.info(f"Estadísticas post-emergencia: {json.dumps(stats_after_emerg, indent=2)}")


        logger.info("Desconectando del PLC...")
        plc.disconnect()
        # Verificar que el worker thread haya terminado
        if plc.worker_thread and plc.worker_thread.is_alive():
            logger.error("El hilo worker del PLC no terminó como se esperaba.")
        else:
            logger.info("Hilo worker del PLC terminado.")

    else:
        logger.error(f"No se pudo conectar al PLC en {PLC_IP_TEST}:{PLC_PORT_TEST} para la prueba.")

    logger.info("Prueba de PLCInterface finalizada.")
