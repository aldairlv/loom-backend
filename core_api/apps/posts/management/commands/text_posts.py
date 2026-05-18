import random
import time
import hashlib
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from blogs.models import Blog
from posts.models import Post, TextBlock, ContentBlockType, Tag

User = get_user_model()

class Command(BaseCommand):
    help = 'Reparte posts de texto entre múltiples usuarios y blogs.'

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS('🚀 Iniciando distribución de posts por usuarios...'))

        posts_data = [
            # --- ARTE Y PINTURA ---
            ("La luz en el impresionismo no es solo un recurso, es el alma de la obra capturando un instante eterno.", ["arte", "pintura", "luz", "impresionismo", "oleo"]),
            ("El lienzo en blanco no es un vacío, es una oportunidad de diálogo entre la emoción y el color.", ["arte", "creatividad", "lienzo", "expresionismo", "color"]),
            ("La técnica del claroscuro define la profundidad humana a través del contraste entre sombra y esperanza.", ["pintura", "tecnica", "barroco", "sombra", "estetica"]),
            ("Pintar es otra forma de llevar un diario; cada pincelada revela un secreto que las palabras callan.", ["arte", "sentimiento", "pincel", "dibujo", "diario"]),
            ("La abstracción permite que el espectador complete la obra con su propia historia y perspectiva.", ["arte", "abstracto", "vision", "concepto", "galeria"]),
            ("El arte urbano transforma el cemento frío en un grito de libertad y color para la comunidad.", ["grafiti", "mural", "ciudad", "arte", "expresion"]),
            ("Dominar la acuarela requiere aceptar que el agua tiene su propia voluntad sobre el papel.", ["acuarela", "tecnica", "agua", "papel", "pintura"]),

            # --- COCINA ---
            ("El secreto de un buen guiso no es la receta, sino la paciencia de dejar que el fuego lento haga su magia.", ["cocina", "sabor", "tradicion", "fuego", "guiso"]),
            ("La cocina es un lenguaje universal donde el aroma a pan recién horneado significa hogar en cualquier idioma.", ["pan", "horno", "aroma", "hogar", "gastronomia"]),
            ("Un equilibrio perfecto entre ácido, sal y grasa puede transformar un ingrediente simple en una joya.", ["cocina", "sabor", "equilibrio", "chef", "receta"]),
            ("La frescura de la albahaca recién cortada eleva cualquier plato de pasta a una experiencia mediterránea.", ["pasta", "hierba", "fresco", "mediterraneo", "cocina"]),
            ("Cocinar para alguien es la forma más honesta y deliciosa de decir 'te quiero' sin usar palabras.", ["cocina", "amor", "detalle", "comida", "chef"]),
            ("El umami es ese quinto sabor que envuelve el paladar y nos conecta con la esencia de los alimentos.", ["sabor", "umami", "paladar", "gastronomia", "ciencia"]),
            ("La repostería es la ciencia exacta de convertir harina y azúcar en felicidad comestible.", ["postre", "dulce", "pastel", "reposteria", "azucar"]),

            # --- MÚSICA ---
            ("El silencio entre las notas es lo que hace que la melodía tenga sentido y respire.", ["musica", "silencio", "melodia", "ritmo", "composicion"]),
            ("Un vinilo girando tiene una calidez que el formato digital jamás podrá replicar por completo.", ["vinilo", "sonido", "retro", "musica", "analogico"]),
            ("El jazz no se escucha con el oído, se siente con el pulso y la libertad de la improvisación.", ["jazz", "ritmo", "improvisacion", "alma", "musica"]),
            ("La armonía de un piano puede calmar la tormenta más ruidosa de la mente humana.", ["piano", "armonia", "paz", "instrumento", "clasico"]),
            ("Cantar es liberar la vibración del alma a través del aire para conectar con el universo.", ["voz", "canto", "vibracion", "energia", "musica"]),
            ("El bajo y la batería son el latido del corazón que mantiene vivo el espíritu del rock.", ["rock", "ritmo", "bateria", "bajo", "concierto"]),
            ("La música es el único túnel del tiempo que nos devuelve a un momento exacto con solo un acorde.", ["recuerdo", "musica", "emocion", "acorde", "tiempo"]),

            # --- TECNOLOGÍA ---
            ("El código limpio es como un buen libro; se lee con fluidez y cuenta una historia de lógica y eficiencia.", ["programacion", "codigo", "software", "tecnologia", "limpieza"]),
            ("La inteligencia artificial no busca reemplazar al humano, sino ampliar las fronteras de nuestra curiosidad.", ["ia", "futuro", "tecnologia", "ciencia", "innovacion"]),
            ("Privacidad no es ocultar algo, es el derecho de elegir qué compartir con el mundo digital.", ["seguridad", "privacidad", "internet", "derechos", "datos"]),
            ("El hardware es el cuerpo, pero el software es el espíritu que da vida a las máquinas.", ["hardware", "software", "computacion", "ingenieria", "digital"]),

            # --- NATURALEZA ---
            ("El bosque no es solo un conjunto de árboles, es una red invisible de vida que se comunica bajo la tierra.", ["naturaleza", "bosque", "ecologia", "vida", "tierra"]),
            ("Observar un atardecer frente al mar nos recuerda que el final de un ciclo también puede ser hermoso.", ["mar", "atardecer", "naturaleza", "reflexion", "paz"]),
            ("Las flores no compiten entre ellas, simplemente florecen cuando les llega su momento.", ["crecimiento", "flores", "jardin", "paciencia", "naturaleza"]),
            ("Cuidar el planeta no es una opción política, es el acto de supervivencia más básico de nuestra especie.", ["sostenibilidad", "planeta", "clima", "conciencia", "futuro"]),

            # --- FILOSOFÍA ---
            ("La felicidad no es un destino, es la habilidad de encontrar asombro en lo cotidiano.", ["felicidad", "filosofia", "mindfulness", "vida", "presente"]),
            ("Tu mente es un jardín: si no plantas flores, las malas hierbas crecerán por su cuenta.", ["psicologia", "mente", "crecimiento", "habitos", "bienestar"]),
            ("El estoicismo no trata de no sentir, sino de entender qué está bajo nuestro control y qué no.", ["estoicismo", "filosofia", "control", "sabiduria", "resiliencia"]),
            ("A veces, avanzar requiere la valentía de soltar lo que ya no nos permite volar.", ["motivacion", "cambio", "libertad", "reflexion", "exito"]),

            # --- DEPORTES ---
            ("El entrenamiento no empieza en el gimnasio, empieza en la decisión de levantarse cuando el cuerpo pide cama.", ["deporte", "fitness", "disciplina", "salud", "esfuerzo"]),
            ("Correr es una meditación en movimiento donde cada paso te aleja del ruido y te acerca a ti mismo.", ["running", "atletismo", "salud", "meditacion", "resistencia"]),
            ("La disciplina tarde o temprano vencerá al talento si este último decide no trabajar duro.", ["disciplina", "exito", "deporte", "mentalidad", "metas"]),
            ("Un cuerpo sano es el vehículo necesario para que una mente brillante pueda viajar lejos.", ["salud", "bienestar", "ejercicio", "equilibrio", "cuerpo"]),

            # --- VIAJES ---
            ("Viajar no es conocer lugares nuevos, es volver con ojos diferentes para mirar lo de siempre.", ["viajes", "aventura", "descubrimiento", "mundo", "cultura"]),
            ("Hay ciudades que no se visitan, se sienten a través de sus calles estrechas y el eco de su historia.", ["viaje", "ciudad", "historia", "turismo", "arquitectura"]),
            ("La mochila pesa menos cuando el corazón va lleno de expectativas y ganas de perderse.", ["aventura", "mochila", "libertad", "viajero", "explorar"]),
            ("El destino es solo una excusa; el verdadero tesoro es la gente que cruzas en el camino.", ["viajes", "personas", "conexiones", "experiencias", "mundo"])
        ]

        # Configuración del reparto
        POSTS_PER_USER = 4
        
        # Dividimos la lista en trozos de 4
        chunks = [posts_data[x:x+POSTS_PER_USER] for x in range(0, len(posts_data), POSTS_PER_USER)]

        for i, chunk in enumerate(chunks):
            # Creamos un usuario único por cada grupo de posts
            username = f'user_tester_{i+1}'
            user, _ = User.objects.update_or_create(
                username=username, 
                defaults={'email': f'{username}@example.com'}
            )

            # Creamos un blog para ese usuario
            blog_name = f'blog-{username}'
            blog, _ = Blog.objects.update_or_create(
                name=blog_name,
                owner=user,
                defaults={'title': f'Espacio de {username.capitalize()}'}
            )

            self.stdout.write(f"👤 Procesando {username} con {len(chunk)} posts...")

            for text, tags in chunk:
                self.create_text_only_post(blog, user, text, tags)

        self.stdout.write(self.style.SUCCESS(f'✅ ¡Script finalizado!'))

    def create_text_only_post(self, blog, user, text_content, tags_list):
        # ID determinista basado en el contenido del texto y usuario
        id_seed = f"{user.username}-{text_content[:30]}"
        post_id = int(hashlib.sha256(id_seed.encode('utf-8')).hexdigest(), 16) % (10**16)

        post, created = Post.objects.update_or_create(
            id=post_id,
            defaults={
                'blogId': blog,
                'timestamp': int(time.time()),
                'likes_count': random.randint(10, 300),
                'reposts_count': random.randint(5, 50),
                'comments_count': random.randint(0, 15),
            }
        )

        # Bloque de texto
        TextBlock.objects.update_or_create(
            post=post,
            order=0,
            defaults={'type': ContentBlockType.TEXT, 'text': text_content}
        )

        # Tags
        if tags_list:
            for tag_name in tags_list:
                tag, _ = Tag.objects.get_or_create(name=tag_name.lower())
                post.tags.add(tag)

        status = "Creado" if created else "Actualizado"
        self.stdout.write(f"  -> {status} en {blog.name}: {text_content[:40]}...")