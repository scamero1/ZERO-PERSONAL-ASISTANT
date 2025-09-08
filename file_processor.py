import os
import io
from typing import Dict, Any, Optional
from PIL import Image
import PyPDF2
import docx
import pandas as pd
import json
from base64 import b64encode

class FileProcessor:
    """Procesador de archivos para extraer contenido y generar análisis"""
    
    SUPPORTED_TYPES = {
        'pdf': ['.pdf'],
        'word': ['.docx', '.doc'],
        'excel': ['.xlsx', '.xls', '.csv'],
        'text': ['.txt', '.md', '.json'],
        'image': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']
    }
    
    @staticmethod
    def get_file_type(filename: str) -> str:
        """Determina el tipo de archivo basado en la extensión"""
        ext = os.path.splitext(filename.lower())[1]
        
        for file_type, extensions in FileProcessor.SUPPORTED_TYPES.items():
            if ext in extensions:
                return file_type
        return 'unknown'
    
    @staticmethod
    def is_supported(filename: str) -> bool:
        """Verifica si el archivo es soportado"""
        return FileProcessor.get_file_type(filename) != 'unknown'
    
    @staticmethod
    def extract_text_from_pdf(file_bytes: bytes) -> str:
        """Extrae texto de un archivo PDF"""
        try:
            pdf_file = io.BytesIO(file_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            
            return text.strip()
        except Exception as e:
            return f"Error al procesar PDF: {str(e)}"
    
    @staticmethod
    def extract_text_from_word(file_bytes: bytes) -> str:
        """Extrae texto de un archivo Word"""
        try:
            doc_file = io.BytesIO(file_bytes)
            doc = docx.Document(doc_file)
            
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            
            return text.strip()
        except Exception as e:
            return f"Error al procesar Word: {str(e)}"
    
    @staticmethod
    def extract_text_from_excel(file_bytes: bytes, filename: str) -> str:
        """Extrae datos de un archivo Excel o CSV"""
        try:
            if filename.lower().endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_bytes))
            else:
                df = pd.read_excel(io.BytesIO(file_bytes))
            
            # Convertir a texto estructurado
            text = f"Archivo: {filename}\n"
            text += f"Dimensiones: {df.shape[0]} filas, {df.shape[1]} columnas\n\n"
            text += "Columnas: " + ", ".join(df.columns.tolist()) + "\n\n"
            text += "Primeras 10 filas:\n"
            text += df.head(10).to_string(index=False)
            
            if df.shape[0] > 10:
                text += f"\n\n... y {df.shape[0] - 10} filas más"
            
            return text
        except Exception as e:
            return f"Error al procesar Excel/CSV: {str(e)}"
    
    @staticmethod
    def extract_text_from_text_file(file_bytes: bytes, filename: str) -> str:
        """Extrae contenido de archivos de texto"""
        try:
            # Intentar diferentes encodings
            encodings = ['utf-8', 'latin-1', 'cp1252']
            
            for encoding in encodings:
                try:
                    text = file_bytes.decode(encoding)
                    
                    # Si es JSON, formatear
                    if filename.lower().endswith('.json'):
                        try:
                            json_data = json.loads(text)
                            text = json.dumps(json_data, indent=2, ensure_ascii=False)
                        except:
                            pass
                    
                    return text
                except UnicodeDecodeError:
                    continue
            
            return "Error: No se pudo decodificar el archivo de texto"
        except Exception as e:
            return f"Error al procesar archivo de texto: {str(e)}"
    
    @staticmethod
    def process_image(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Procesa una imagen y extrae información básica"""
        try:
            image = Image.open(io.BytesIO(file_bytes))
            
            # Información básica de la imagen
            info = {
                'filename': filename,
                'format': image.format,
                'mode': image.mode,
                'size': image.size,
                'width': image.width,
                'height': image.height
            }
            
            # Convertir a base64 para análisis posterior
            image_base64 = b64encode(file_bytes).decode('utf-8')
            info['base64'] = image_base64
            
            # Descripción textual
            description = f"Imagen: {filename}\n"
            description += f"Formato: {image.format}\n"
            description += f"Dimensiones: {image.width}x{image.height} píxeles\n"
            description += f"Modo de color: {image.mode}"
            
            info['description'] = description
            
            return info
        except Exception as e:
            return {
                'filename': filename,
                'error': f"Error al procesar imagen: {str(e)}"
            }
    
    @staticmethod
    def process_file(file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Procesa un archivo y extrae su contenido"""
        file_type = FileProcessor.get_file_type(filename)
        file_size = len(file_bytes)
        
        result = {
            'filename': filename,
            'file_type': file_type,
            'file_size': file_size,
            'content': None,
            'metadata': {},
            'error': None
        }
        
        try:
            if file_type == 'pdf':
                result['content'] = FileProcessor.extract_text_from_pdf(file_bytes)
            elif file_type == 'word':
                result['content'] = FileProcessor.extract_text_from_word(file_bytes)
            elif file_type == 'excel':
                result['content'] = FileProcessor.extract_text_from_excel(file_bytes, filename)
            elif file_type == 'text':
                result['content'] = FileProcessor.extract_text_from_text_file(file_bytes, filename)
            elif file_type == 'image':
                image_info = FileProcessor.process_image(file_bytes, filename)
                result['content'] = image_info.get('description', '')
                result['metadata'] = image_info
            else:
                result['error'] = f"Tipo de archivo no soportado: {file_type}"
                
        except Exception as e:
            result['error'] = f"Error al procesar archivo: {str(e)}"
        
        return result
    
    @staticmethod
    def generate_summary(content: str, file_type: str) -> str:
        """Genera un resumen del contenido del archivo"""
        if not content or len(content.strip()) == 0:
            return "Archivo vacío o sin contenido extraíble"
        
        # Resumen básico basado en el tipo de archivo
        lines = content.split('\n')
        total_lines = len(lines)
        total_chars = len(content)
        
        summary = f"Resumen del archivo ({file_type.upper()}):\n"
        summary += f"- Líneas: {total_lines}\n"
        summary += f"- Caracteres: {total_chars}\n"
        
        if file_type == 'excel':
            if 'filas' in content and 'columnas' in content:
                # Extraer información de dimensiones
                for line in lines[:5]:
                    if 'Dimensiones:' in line:
                        summary += f"- {line.strip()}\n"
                    elif 'Columnas:' in line:
                        summary += f"- {line.strip()}\n"
        
        # Primeras líneas como preview
        preview_lines = lines[:3]
        if preview_lines:
            summary += "\nVista previa:\n"
            for line in preview_lines:
                if line.strip():
                    summary += f"  {line.strip()[:100]}...\n"
        
        return summary