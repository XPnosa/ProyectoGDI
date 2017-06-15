#-*- coding: utf-8 -*-

from django.core.management.base import BaseCommand, CommandError

from pgdiapp.models import Configuracion, Mensaje, Tipo

class Command(BaseCommand):
	help = 'Script que se debe ejecutar para completar la instalación de PGDI'

	def handle(self, *args, **options):
		try:
			# Poblando Configuraciones
			Configuracion(clave='openregister',info='Si se establece a True, se habilitará el formulario de registro y el cuestionario.',valor=True).save()
			Configuracion(clave='freeusername',info='Si se establece a True, se podrá elegir el nombre de usuario durante el registro.',valor=False).save()
			# Poblando Mensajes
			Mensaje(cod='WELCOME',asunto='Bienvenid@',cuerpo='Hola {{USUARIO}}, bienvenid@ al curso de {{GRADO}}').save()
			Mensaje(cod='BYEBYE',asunto='Aviso de baja',cuerpo='Tu usuario {{USUARIO}} ha sido dado de baja del curso de {{GRADO}}').save()
			# Poblando Tipos
			Tipo(clase='error').save()
			Tipo(clase='info').save()
			Tipo(clase='success').save()
			Tipo(clase='warn').save()
			print "\nLa base de datos se pobló correctamente.\n"
		except:
			print "\nOcurrió un error al poblar la base de datos.\n"
			raise
