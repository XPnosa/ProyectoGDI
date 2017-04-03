from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from localflavor.es.forms import ESIdentityCardNumberField

# Modelos

class Taller(models.Model):
	cod = models.CharField(max_length=5, unique=True)
	numero = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(4)])
	info = models.TextField(default=None, blank=True, null=True)
	def __str__(self):
		return str(self.cod)
	class Meta:
		ordering = ["cod"]
		verbose_name_plural = "Talleres"

class Grado(models.Model):
	cod = models.CharField(max_length=5, unique=True)
	nombre = models.CharField(max_length=200, unique=True)
	nocturno = models.BooleanField(default=False)
	def __str__(self):
		return str(self.cod)
	class Meta:
		ordering = ["cod"]
		verbose_name_plural = "Grados"

class Clase(models.Model):
	grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
	taller = models.ForeignKey(Taller, on_delete=models.CASCADE)
	curso = models.IntegerField(validators=[MinValueValidator(1),MaxValueValidator(2)])
	def __str__(self):
		return str(self.grado) + " - " + str(self.taller)
	class Meta:
		ordering = ["grado","taller"]
		unique_together = ('grado', 'taller')
		verbose_name_plural = "Clases"

class Perfil(models.Model):
	user = models.ForeignKey(User, on_delete=models.CASCADE)
	grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
	info = models.TextField(default=None, blank=True, null=True)
	dni_regex = RegexValidator(regex=r'^[0-9]{8}[a-zA-Z]{1}$')
	dni = models.CharField(max_length=9, validators=[dni_regex], unique=True, null=False)
	nombre = models.CharField(max_length=50, null=False)
	apellido1 = models.CharField(max_length=50, null=False)
	apellido2 = models.CharField(max_length=50, null=False)
	tel_regex = RegexValidator(regex=r'^\+?1?\d{9}$')
	telefono = models.CharField(max_length=9, validators=[tel_regex], null=True)
	email = models.EmailField(null=False)
	fecha_nac = models.DateField(null=True)
	validado = models.BooleanField(default=False)
	def __str__(self):
		return str(self.user.username)
	class Meta:
		ordering = ["user"]
		unique_together = ('user','grado')
		verbose_name_plural = "Perfiles"

class Pregunta(models.Model):
	texto = models.CharField(max_length=300, null=False)
	def __str__(self):
		return str(self.texto)
	class Meta:
		ordering = ["texto"]
		verbose_name_plural = "Preguntas"

class Cuestionario(models.Model):
	grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
	pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
	def __str__(self):
		return str(self.grado)+": "+str(self.pregunta)
	class Meta:
		ordering = ["grado",'pregunta']
		unique_together = ('grado','pregunta')
		verbose_name_plural = "Cuestionarios"

class Respuesta(models.Model):
	alumno = models.ForeignKey(Perfil, on_delete=models.CASCADE)
	pregunta = models.ForeignKey(Pregunta, on_delete=models.CASCADE)
	texto = models.CharField(max_length=300, null=False)
	def __str__(self):
		return str(self.alumno)+" - "+str(self.pregunta)+": "+str(self.texto)
	class Meta:
		ordering = ["alumno","pregunta"]
		unique_together = ('alumno','pregunta')
		verbose_name_plural = "Respuestas"

class Configuracion(models.Model):
	clave = models.CharField(max_length=100, unique=True)
	info = models.TextField(default=None, blank=True, null=True)
	valor = models.BooleanField(default=False)
	def __str__(self):
		return str(self.clave)
	class Meta:
		ordering = ["clave"]
		verbose_name_plural = "Configuraciones"
