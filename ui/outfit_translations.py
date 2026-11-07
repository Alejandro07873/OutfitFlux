"""Translations shared by secondary OutfitFlux screens."""
from PySide6 import QtCore, QtWidgets as W
from services.config_service import load_config

TEXT = {
'Personaje / Character':'Character','Nombre del mod / Mod name':'Mod name','Personalizado / Custom':'Custom',
'PAK del juego / Game PAK':'Game PAK','Carpeta de exportación / Export folder':'Export folder','Character de FModel / FModel Character':'FModel Character',
'OutfitFlux · Configuración / Setup':'OutfitFlux · Setup',
'Elige un traje y exporta. El mod original se conserva.':'Choose costumes and export. Your original mod is preserved.',
'Importa un mod PAK para continuar.':'Import a PAK mod to continue.',
'Experimental: no adapta huesos ni física.':'Experimental: bones and physics are not adapted.',
'TU MOD. TU ESTILO.':'YOUR MOD. YOUR STYLE.',
'También puedes arrastrar tu archivo .pak a esta ventana.':'You can also drop your .pak file into this window.',
'Actualizar catálogo / Update catalog':'Update catalog',
'Inspeccionar PAK':'Inspect PAK','Detectar conflictos':'Find conflicts','Extraer PAK':'Extract PAK',
'Empaquetar carpeta':'Pack folder','Indexar FModel':'Index FModel','Referencias de asset':'Asset references',
'Historial':'History','Diagnóstico':'Diagnostics','Ajustes':'Settings','Actualizar catálogo':'Update catalog',
'Preparar biblioteca':'Prepare library','Recargar biblioteca':'Reload library',
'Archivos, personajes, mallas y archivos huérfanos':'Files, characters, meshes and orphaned files',
'Rutas compartidas entre varios mods':'Paths shared by multiple mods',
'Carpeta nueva; conserva el original':'New folder; preserves the original',
'Crear PAK con verificación de contenido':'Create PAK with content verification',
'Inventario de mallas y archivos asociados':'Mesh and associated file inventory',
'Materiales, esqueleto y física desde JSON':'Materials, skeleton and physics from JSON',
'Resultados y errores de exportación':'Export results and errors',
'Herramientas y biblioteca local':'Tools and local library',
'PAK del juego, AES e idioma de la vista clásica':'Game PAK, AES and language',
'Actualizador original de nombres EN/ES':'English and Spanish costume names',
'Extracción original del juego y miniaturas':'Game assets and thumbnails',
'Releer catálogo y rutas PA':'Reload catalog and PA paths',
'Cancelar':'Cancel','Revisar exportación':'Review export',
'Elegir carpeta y exportar':'Choose folder and export','Carpeta de salida':'Output folder',
'Guardar informe JSON':'Save JSON report','Guardar informe':'Save report',
'Quitar de favoritos':'Remove favorite','Añadir a favoritos':'Add favorite','Ver ruta y detalles':'View path and details',
'Detalles del traje':'Costume details','Importar mod':'Import mod',
'Elige personaje…':'Choose character…',
'Crear una carpeta por personaje / Create a folder per character':'Create a folder per character',
'Crear carpeta para este lote / Create batch folder':'Create batch folder',
'Se conservará el PAK original. Los nombres existentes recibirán un contador.\nSe verifica el contenido del PAK; el resultado visual necesita comprobarse en el juego.':'The original PAK is preserved. Existing names receive a counter.\nPAK contents are verified; visual results must be checked in game.',
'Acepto la reasignación experimental entre personajes; no adapta huesos ni física.':'Enable experimental cross-character reassignment; bones and physics are not adapted.'
}

TEXT.update({
'Confirma el intercambio entre personajes antes de exportar.':'Confirm the cross-character swap before exporting.',
'Selecciona una ruta de salida.':'Select an output path.',
'UEJSON no devolvió un documento de asset válido.':'UEJSON did not return a valid asset document.',
'No se encontró el objeto exacto de la malla; no se aplicará un reemplazo ambiguo.':'The exact mesh object was not found; an ambiguous replacement will not be applied.',
'La malla seleccionada no pertenece al mod.':'The selected mesh does not belong to this mod.',
'No se reconstruyó la malla de salida.':'The output mesh was not rebuilt.',
'La salida no puede estar dentro de los archivos que se empaquetan.':'The output cannot be inside the folder being packed.',
'No hay archivos para empaquetar.':'There are no files to pack.',
'No se admiten enlaces a archivos externos.':'Links to external files are not supported.',
'Ruta no válida para UnrealPak.':'Invalid path for UnrealPak.',
'UnrealPak no produjo un archivo válido.':'UnrealPak did not produce a valid file.',
'El contenido del PAK no coincide con el manifiesto de exportación.':'The PAK contents do not match the export manifest.',
'La salida no puede reemplazar el mod original ni el PAK del juego.':'The output cannot replace the original mod or game PAK.',
'El origen contiene enlaces externos.':'The source contains external links.',
'UEJSON no creó el documento de la malla.':'UEJSON did not create the mesh document.',
'Todo lo que necesitas para preparar, revisar y organizar tus mods.':'Everything you need to prepare, inspect and organize your mods.',
'Idioma, apariencia y rutas del juego':'Language, appearance and game paths',
'Solo novedades y archivos que necesitan reparación':'Only new content and files that need repair',
'Campo':'Field','Valor':'Value','Buscar en los resultados…':'Search results…',
'Ver JSON':'View JSON','Vista organizada':'Structured view',
'Confirmar intercambio entre personajes.':'Confirm cross-character swap.',
'Intercambio entre personajes · Comprueba el resultado en el juego.':'Cross-character swap · Check the result in game.',
'Operación':'Operation','Operación cancelada.':'Operation cancelled.',
'Esperando a que termine la operación antes de cerrar…':'Waiting for the operation to finish before closing…',
'Inspeccionando mod…':'Inspecting mod…','PAK sin malla intercambiable':'PAK has no swappable mesh',
'Mod con varias mallas':'Mod with multiple meshes','Malla que quieres reasignar; las demás se conservarán:':'Choose the mesh to reassign; other meshes are preserved:',
'Elige el personaje de destino.':'Choose the destination character.','No hay trajes para esta selección.':'No costumes match this selection.',
'Cola de destinos — varios personajes':'Destination queue — multiple characters','Quitar seleccionados':'Remove selected',
'Guardar perfil':'Save preset','Guardar destinos':'Save destinations','Perfil':'Preset','Cargar perfil':'Load preset','Cargar destinos':'Load destinations',
'El archivo no es un perfil de destinos compatible.':'The file is not a supported destination preset.',
'Destinos no disponibles':'Unavailable destinations','Revisar y exportar cola':'Review and export queue',
'Categoría de intercambio':'Swap category','La cola incluye destinos de otra categoría. Usa Trajes para el mismo personaje y Entre personajes para los demás.':'The queue contains destinations from another category. Use Costumes for the same character and Cross-character for others.',
'Destinos':'Destinations','Todos los destinos coinciden con el origen.':'All destinations match the source.',
'Exportando destinos…':'Exporting destinations…','Exportación':'Export','Error al exportar':'Export failed',
'Reemplazar archivo / Replace file':'Replace file','Error al guardar':'Save failed','Inspeccionando…':'Inspecting…',
'Selecciona dos o más mods':'Select two or more mods','Comparando rutas…':'Comparing paths…',
'Conflictos de rutas (no compara contenido)':'Path conflicts (does not compare contents)',
'Carpeta donde crear la extracción':'Folder for extracted files','Extrayendo…':'Extracting…','Extracción terminada':'Extraction complete',
'Carpeta que contiene HerovsGame':'Folder containing HerovsGame','Estructura del mod':'Mod structure',
'Selecciona una carpeta que contenga HerovsGame/Content.':'Select a folder containing HerovsGame/Content.',
'Nuevo PAK (no se sobrescriben archivos)':'New PAK (existing files are preserved)','Empaquetando…':'Packing…','PAK verificado':'PAK verified',
'Carpeta Character de FModel':'FModel Character folder','Indexando FModel…':'Indexing FModel…','Inventario FModel':'FModel inventory',
'Asset exportado como JSON':'Asset exported as JSON','Leyendo referencias…':'Reading references…','Referencias declaradas':'Declared references',
'Comprobando herramientas…':'Checking tools…','Actualizando catálogo…':'Updating catalog…','PAK del juego':'Game PAK',
'Configura primero una ruta válida en Ajustes.':'Set a valid path in Settings first.',
'Preparando biblioteca…':'Preparing library…','Biblioteca preparada':'Library ready',
'Finalizado':'Complete','Cancelado':'Cancelled','Extrayendo el origen una sola vez…':'Extracting source once…',
'Preparando…':'Preparing…',
'Leyendo solo recursos del catálogo / Reading only catalog resources':'Reading only catalog resources',
'Leyendo recursos del catálogo / Reading catalog resources':'Reading catalog resources',
'Verificando caché / Checking cache':'Checking cache',
'Leyendo índice / Reading index':'Reading index','Comprobando contenido del juego / Checking game contents':'Checking game contents',
'Actualizando archivos / Updating files':'Updating files','Preparando catálogo / Preparing catalog':'Preparing catalog',
'Guardar':'Save','Cerrar':'Close','Sí':'Yes','No':'No','Aceptar':'OK',
'Catálogo / Catalog':'Catalog','Catálogo al día / Catalog up to date':'Catalog up to date',
'Personaje':'Character','Nombre del mod':'Mod name','Personalizado':'Custom',
})

def tr_text(text, english=None):
    if english is None:
        english = load_config().get('language','es') == 'en'
    reverse = {value:key for key,value in TEXT.items()}
    source = reverse.get(text,text)
    if source in TEXT:
        return TEXT[source] if english else source.split(' / ')[0]
    return text

class ScreenTranslator(QtCore.QObject):
    def eventFilter(self, obj, event):
        if event.type() == QtCore.QEvent.Type.Show and isinstance(obj,W.QWidget):
            self.translate(obj, load_config().get('language','es') == 'en')
        return False
    def translate(self, root, english=True):
        reverse = {value:key for key,value in TEXT.items()}
        def translated(text):
            if text in reverse:
                text = reverse[text]
            if text in TEXT:
                return TEXT[text] if english else text.split(' / ')[0]
            return '\n'.join((TEXT.get(reverse.get(line,line),reverse.get(line,line)) if english else (reverse.get(line,line).split(' / ')[0] if reverse.get(line,line) in TEXT else line)) for line in text.split('\n'))
        for widget in [root] + root.findChildren(W.QWidget):
            if isinstance(widget,(W.QLabel,W.QAbstractButton)):
                widget.setText(translated(widget.text()))
            widget.setWindowTitle(translated(widget.windowTitle()))
            if isinstance(widget,W.QComboBox):
                for index in range(widget.count()):
                    widget.setItemText(index,translated(widget.itemText(index)))
            for action in widget.actions():
                action.setText(translated(action.text()))
