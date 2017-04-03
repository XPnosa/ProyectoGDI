from django.shortcuts import render, redirect, render_to_response 
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django_auth_ldap.config import LDAPSearch, PosixGroupType

from .forms import UserProfileForm, RespuestaForm
from .models import *

from datetime import datetime
import ldap

# Vistas
def index(request):
	openrg = Configuracion.objects.get(clave='openregister').valor
	freeun = Configuracion.objects.get(clave='freeusername').valor
	return render(request, 'pgdiapp/index.html', { 'openrg':openrg, 'freeun':freeun })

# Habilitar/Deshabilitar el registro
def regmod(request):
	openrg = Configuracion.objects.get(clave='openregister')
	if openrg.valor:
		openrg.valor = False
	else:
		openrg.valor = True
	openrg.save()
	return redirect('/app')

# Habilitar/Deshabilitar la eleccion del nombre de usuario
def funmod(request):
	freeun = Configuracion.objects.get(clave='freeusername')
	if freeun.valor:
		freeun.valor = False
	else:
		freeun.valor = True
	freeun.save()
	return redirect('/app')

# Listado de alumnos validados
def alumnos(request):
	try:
		grupos = request.user.ldap_user.group_names
	except:
		return redirect('/app')
	if 'ASIR' in grupos:
		grado = 'ASIR'
	elif 'DAM' in grupos:
		grado = 'DAM'
	elif 'SMR' in grupos:
		grado = 'SMR'
	alumnos = ldap_search('pgdi',ldap.VERSION3,"ou="+grado+",ou=alumnos,ou=usuarios,dc=pgdi,dc=inf",ldap.SCOPE_ONELEVEL,None,"(objectClass=*)")
	return render(request, 'pgdiapp/alumnos.html', { 'alumnos': alumnos, 'grado':grado })

# Entrada al perfil
def perfil(request, grado, usuario):
	alumno = ldap_search('pgdi',ldap.VERSION3,"ou="+grado+",ou=alumnos,ou=usuarios,dc=pgdi,dc=inf",ldap.SCOPE_ONELEVEL,None,"(uid="+usuario+")")
	return render(request, 'pgdiapp/perfil.html', { 'alumno': alumno, 'grado':grado })

# Pre-registro de un nuevo alumno
def register(request):
	ip = request.META['REMOTE_ADDR']
	hora = datetime.now().strftime('%H')
	grado = obtener_grado(ip, hora)
	freeun = Configuracion.objects.get(clave='freeusername').valor
	openrg = Configuracion.objects.get(clave='openregister').valor
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
	return render(request, 'pgdiapp/user_form.html', { 'uform': uform, 'pform': pform, 'grado':grado, 'ip':ip, 'freeun':freeun, 'openrg':openrg })

# Formularo de preguntas
def cuestionario(request, user_name):
	usuario = User.objects.get(username=user_name)
	perfil = Perfil.objects.get(user=usuario)
	preguntas = Cuestionario.objects.filter(grado=perfil.grado)
	RespuestaFormSet = formset_factory(RespuestaForm, extra=len(preguntas))
	openrg = Configuracion.objects.get(clave='openregister').valor
	if request.method == 'POST':
		respuestas = RespuestaFormSet(request.POST)
		if respuestas.is_valid():
			for respuesta in respuestas:
				respuesta.save()
			return render(request, 'pgdiapp/registro_completo.html', { 'alumno': perfil })
	else:
		respuestas = RespuestaFormSet()
	return render(request, 'pgdiapp/cuestionario.html', { 'alumno':perfil, 'preguntas':preguntas, 'respuestas':RespuestaFormSet, 'openrg':openrg })

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

# Busqueda de datos en ldap
def ldap_search(server,version,baseDN,searchScope,retrieveAttributes,searchFilter):
	l = ldap.open(server)
	l.protocol_version = version
	ldap_result_id = l.search(baseDN, searchScope, searchFilter, retrieveAttributes)
	result_set = []
	while True:
		result_type, result_data = l.result(ldap_result_id, 0)
		if (result_data == []):
			break
		else:
			if result_type == ldap.RES_SEARCH_ENTRY:
				result_set.append(result_data)
	return result_set

# Cambiar password (TODO)
def pwmod(request):
	return redirect('/app')

# Login
def login_view(request):
	if request.method == 'POST':
		username = request.POST['username']
		password = request.POST['password']
		user = authenticate(username=username, password=password)
		if user is not None:
			login(request, user)
			try:
				perfil = Perfil.objects.get(user__username=username)
			except:
				return redirect('/app')
			return HttpResponseRedirect("/app/perfil/"+perfil.grado.cod+"/"+username)
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
