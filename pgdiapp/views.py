from django.shortcuts import render, redirect, render_to_response 
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory

from .forms import UserProfileForm, RespuestaForm
from .models import *

from datetime import datetime

# Vistas

def index(request):
	return render(request, 'pgdiapp/index.html')

# Entrada al perfil
def perfil(request, user_name):
	alumno = Perfil.objects.get(user__username=user_name)
	grado = Grado.objects.get(cod=alumno.grado)
	return render(request, 'pgdiapp/perfil.html', { 'alumno': alumno, 'grado':grado })

# Pre-registro de un nuevo alumno
def register(request):
	ip = request.META['REMOTE_ADDR']
	hora = datetime.now().strftime('%H')
	grado = obtener_grado(ip, hora)
	freeun = True
	if request.method == 'POST':
		uform = UserCreationForm(request.POST)
		pform = UserProfileForm(data = request.POST)
		if uform.is_valid() and pform.is_valid():
			user = uform.save(commit = False)
			profile = pform.save(commit = False)
			if not freeun:
				user.username = generar_username(profile.nombre,profile.apellido1,profile.apellido2)
			user.save()
			profile.user = user
			profile.save()
			return HttpResponseRedirect("/app/cuestionario/"+str(user.username))
	else:
		uform = UserCreationForm()
		pform = UserProfileForm()
	return render(request, 'pgdiapp/user_form.html', { 'uform': uform, 'pform': pform, 'grado':grado, 'ip':ip, 'freeun':freeun })

# Formularo de preguntas
def cuestionario(request, user_name):
	usuario = User.objects.get(username=user_name)
	perfil = Perfil.objects.get(user=usuario)
	preguntas = Cuestionario.objects.filter(grado=perfil.grado)
	RespuestaFormSet = formset_factory(RespuestaForm, extra=len(preguntas))
	if request.method == 'POST':
		respuestas = RespuestaFormSet(request.POST)
		if respuestas.is_valid():
			for respuesta in respuestas:
				respuesta.save()
			return HttpResponseRedirect("/app/perfil/"+perfil.user.username)
	else:
		respuestas = RespuestaFormSet()
	return render(request, 'pgdiapp/cuestionario.html', { 'alumno':perfil, 'preguntas':preguntas, 'respuestas':RespuestaFormSet })

# Obtencion del grado por taller
def obtener_grado(ip, hora):
	if int(hora) > 15:
		es_nocturno = True
	else:
		es_nocturno = False
	try:
		grado = Clase.objects.get(taller__numero=ip[8:9], grado__nocturno=es_nocturno).grado.cod
	except:
		grado = 'desconocido'
	return grado

# Generacion del nombre del usuario
def generar_username(nom, ap1, ap2):
	while nom.find(' ') > 0:
		nom = nom.replace(' ', '')
	while ap1.find(' ') > 0:
		ap1 = ap1.replace(' ', '')
	while ap2.find(' ') > 0:
		ap2 = ap2.replace(' ', '')
	return (nom+ap1[:2]+ap2[:2]).lower()

# Cambiar password (TODO)
def pwmod(request):
	return redirect('/app')

# Login (TODO)
def login_view(request):
	if request.method == 'POST':
		username = request.POST['username']
		password = request.POST['password']
		user = authenticate(username=username, password=password)
		if user is not None:
			login(request, user)
			return HttpResponseRedirect("/app/perfil/"+username)
		else:
			return redirect('/app/error')
	else:
		return render(request, 'pgdiapp/login.html')

def error(request):
	return render(request, 'pgdiapp/error.html')

# Logout
def logout_view(request):
	logout(request)
	return redirect('/app/logout_redirect')

def logoutr(request):
	return render(request, 'pgdiapp/logout.html')
