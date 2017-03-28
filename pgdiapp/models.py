from __future__ import unicode_literals
from django.contrib.auth.models import User
from django.db import models
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator

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
	user = models.OneToOneField(User, unique=True, on_delete=models.CASCADE)
	grado = models.ForeignKey(Grado, on_delete=models.CASCADE)
	info = models.TextField(default=None, blank=True, null=True)
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
		verbose_name_plural = "Perfiles"

class Pregunta(models.Model):
	grado = models.OneToOneField(Grado, on_delete=models.CASCADE, unique=True,)
	p1 = models.CharField(max_length=300, null=False)
	p2 = models.CharField(max_length=300, null=False)
	p3 = models.CharField(max_length=300, null=False)
	p4 = models.CharField(max_length=300, null=False)
	p5 = models.CharField(max_length=300, null=False)
	p6 = models.CharField(max_length=300, null=False)
	p7 = models.CharField(max_length=300, null=False)
	p8 = models.CharField(max_length=300, null=False)
	p9 = models.CharField(max_length=300, null=False)
	def __str__(self):
		return str(self.grado)
	class Meta:
		ordering = ["grado"]
		verbose_name_plural = "Preguntas"

class Respuesta(models.Model):
	alumno = models.OneToOneField(Perfil, on_delete=models.CASCADE, unique=True,)
	r1 = models.CharField(max_length=300, null=False)
	r2 = models.CharField(max_length=300, null=False)
	r3 = models.CharField(max_length=300, null=False)
	r4 = models.CharField(max_length=300, null=False)
	r5 = models.CharField(max_length=300, null=False)
	r6 = models.CharField(max_length=300, null=False)
	r7 = models.CharField(max_length=300, null=False)
	r8 = models.CharField(max_length=300, null=False)
	r9 = models.CharField(max_length=300, null=False)
	def __str__(self):
		return str(self.alumno)
	class Meta:
		ordering = ["alumno"]
		verbose_name_plural = "Respuestas"
