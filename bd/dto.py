from pydantic import BaseModel
from typing import Optional, Dict, List
from enum import Enum
from datetime import datetime

# Enums basados en las definiciones de la base de datos
class PerfilAprendizajeEnum(str, Enum):
    VISUAL = "Visual"
    AUDITIVO = "Auditivo"
    LECTOR = "Lector"
    KINESTESICO = "Kinestesico"

class NivelEnum(str, Enum):
    PRIMARIA = "Primaria"
    SECUNDARIA = "Secundaria"
    PREGRADO = "Pregrado"
    POSGRADO = "Posgrado"

class TipoSesionEnum(str, Enum):
    CLASE_TEORICA = "Clase teorica"
    TALLER_PRACTICO = "Taller practico"
    SESION_REPASO = "Sesion de repaso"
    EVALUACION_FORMATIVA = "Evaluacion formativa"
    SESION_INTEGRACION = "Sesion de integracion"

class ModalidadEnum(str, Enum):
    PRESENCIAL = "Presencial"
    HIBRIDA = "Hibrida"
    VIRTUAL_SINCRONICA = "Virtual sincronica"
    VIRTUAL_ASINCRONICA = "Virtual asincronica"

class ResultadoTaxonomiaEnum(str, Enum):
    RECORDAR = "Recordar"
    COMPRENDER = "Comprender"
    APLICAR = "Aplicar"
    ANALIZAR = "Analizar"
    EVALUAR = "Evaluar"
    CREAR = "Crear"

class EstiloContenidoEnum(str, Enum):
    FORMAL_ACADEMICO = "Formal academico"
    CERCANO_MOTIVADOR = "Cercano y motivador"
    PRACTICO_DIRECTO = "Practico y directo"
    NARRATIVO_STORYTELLING = "Narrativo/Storytelling"

class TipoArchivoEnum(str, Enum):
    SUBIDO = "Subido"
    GENERADO = "Generado"

# DTOs para Docente
class DocenteCreateDTO(BaseModel):
    nombre: str
    correo: str
    password: str

class DocenteResponseDTO(BaseModel):
    id: int
    nombre: str
    correo: str

class DocenteLoginDTO(BaseModel):
    correo: str
    password: str

# DTOs para Formulario
class FormularioCreateDTO(BaseModel):
    enlace: str
    cantidad_visual: Optional[int] = 0
    cantidad_auditivo: Optional[int] = 0
    cantidad_lector: Optional[int] = 0
    cantidad_kinestesico: Optional[int] = 0

class FormularioResponseDTO(BaseModel):
    id: int
    enlace: str
    cantidad_visual: Optional[int] = None
    cantidad_auditivo: Optional[int] = None
    cantidad_lector: Optional[int] = None
    cantidad_kinestesico: Optional[int] = None
    fecha_creacion: Optional[datetime] = None
    fecha_cierre: Optional[datetime] = None
    estado: Optional[bool] = None

# DTOs para las tablas
class ClaseCreateDTO(BaseModel):
    id_formulario: int
    id_docente: int
    nombre: Optional[str] = None
    perfil: PerfilAprendizajeEnum
    area: Optional[str] = None
    tema: Optional[str] = None
    nivel_educativo: Optional[NivelEnum] = None
    duracion_estimada: Optional[int] = None
    solo_informacion_proporcionada: Optional[bool] = None
    conocimientos_previos_estudiantes: Optional[str] = None
    tipo_sesion: Optional[TipoSesionEnum] = None
    modalidad: Optional[ModalidadEnum] = None
    objetivos_aprendizaje: Optional[str] = None
    resultado_taxonomia: Optional[ResultadoTaxonomiaEnum] = None
    recursos: Optional[str] = None
    aspectos_motivacionales: Optional[str] = None
    estilo_material: Optional[EstiloContenidoEnum] = None
    tipo_recursos_generar: Optional[str] = None

class ClaseResponseDTO(BaseModel):
    id: int
    id_formulario: int
    id_docente: int
    nombre: Optional[str] = None
    perfil: PerfilAprendizajeEnum
    area: Optional[str] = None
    tema: Optional[str] = None
    nivel_educativo: Optional[NivelEnum] = None
    duracion_estimada: Optional[int] = None
    solo_informacion_proporcionada: Optional[bool] = None
    conocimientos_previos_estudiantes: Optional[str] = None
    tipo_sesion: Optional[TipoSesionEnum] = None
    modalidad: Optional[ModalidadEnum] = None
    objetivos_aprendizaje: Optional[str] = None
    resultado_taxonomia: Optional[ResultadoTaxonomiaEnum] = None
    recursos: Optional[str] = None
    aspectos_motivacionales: Optional[str] = None
    estilo_material: Optional[EstiloContenidoEnum] = None
    tipo_recursos_generar: Optional[str] = None
    estado: Optional[bool] = None

class ContenidoCreateDTO(BaseModel):
    id_clase: int
    tipo_recurso_generado: Optional[str] = None
    contenido: Optional[str] = None

class ContenidoResponseDTO(BaseModel):
    id: int
    id_clase: int
    tipo_recurso_generado: Optional[str] = None
    contenido: Optional[str] = None
    estado: Optional[bool] = None

# DTOs para Archivo
class ArchivoCreateDTO(BaseModel):
    id_clase: Optional[int] = None
    id_silabo: Optional[int] = None
    filename: str
    tipo: TipoArchivoEnum

class ArchivoResponseDTO(BaseModel):
    id: int
    id_clase: Optional[int] = None
    id_silabo: Optional[int] = None
    filename: str
    tipo: TipoArchivoEnum

