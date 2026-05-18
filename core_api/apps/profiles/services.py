# profiles/services.py


# profiles/services.py
from django.db import transaction
from PIL import Image
import os

def set_new_default(user, new_profile):
    with transaction.atomic():
        # 1. Quitar el flag de todos los perfiles del usuario
        user.profiles.filter(is_default=True).update(is_default=False)
        
        # 2. Poner el flag al nuevo perfil
        new_profile.is_default = True
        new_profile.save()



"""def process_image(image_path, size=(500, 500)):
    
    #Abre la imagen, la redimensiona manteniendo la proporción y la guarda.
    
    if not os.path.exists(image_path):
        return

    with Image.open(image_path) as img:
        # Convertir a RGB (evita errores con PNGs transparentes al guardar como JPEG)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        img.thumbnail(size) # Mantiene la relación de aspecto
        img.save(image_path, 'JPEG', quality=85)"""