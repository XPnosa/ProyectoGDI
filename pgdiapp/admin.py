from django.contrib import admin
from .models import Clase, Grado, Perfil, Taller, Pregunta, Respuesta, Cuestionario, Configuracion

admin.site.register(Clase)
admin.site.register(Grado)
admin.site.register(Perfil)
admin.site.register(Taller)
admin.site.register(Pregunta)
admin.site.register(Respuesta)
admin.site.register(Cuestionario)
admin.site.register(Configuracion)
