#-*- coding: utf-8 -*-

from django.shortcuts import render, redirect, render_to_response 
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest

from .forms import *
from .models import *

from utiles import *

# Descartar alumnos pre-registrados
def confirmar_descarte(request, grado, usuario):
	if request.user.is_staff:
		return render(request, 'pgdiapp/confirmar_descarte.html', { 'alumno': usuario, 'grado':grado })

def descarte(request, grado, usuario):
	if request.user.is_staff:
		descarte_efectivo(grado, usuario)
		return render(request, 'pgdiapp/descarte.html', { 'alumno': usuario, 'grado':grado })

def descarte_efectivo(grado, usuario):
	alumno = User.objects.get(username=usuario)
	if es_exalumno(usuario):
		exalumno = Perfil.objects.get(user__username=usuario)
		respuestas = Respuesta.objects.filter(alumno=exalumno)
		for respuesta in respuestas:
			respuesta.delete()
		exalumno.grado = None
		exalumno.save()
	else:
		alumno = User.objects.get(username=usuario)
		alumno.delete()
