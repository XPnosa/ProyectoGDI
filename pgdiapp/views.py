#-*- coding: utf-8 -*-

from django.shortcuts import render, redirect, render_to_response 
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django_auth_ldap.config import LDAPSearch, PosixGroupType
from django.conf import settings

from datetime import datetime

from .forms import *
from .models import *

from altas import *
from bajas import *
from descartes import *
from correos import *
from cuotas import *
from utiles import *

import ldap, copy, crypt, string, random, unicodedata, base64, smtplib, subprocess
import ldap.modlist as modlist

# Vistas
def index(request):
	openrg = Configuracion.objects.get(clave='openregister').valor
	freeun = Configuracion.objects.get(clave='freeusername').valor
	return render(request, 'pgdiapp/index.html', { 'openrg':openrg, 'freeun':freeun })

# Listado de alumnos validados
def alumnos(request):
	try:
		grupos = request.user.ldap_user.group_names
	except:
		return redirect('/app/login')
	l_grados = obtener_grados(grupos)
	# Operaciones múltiples
	if request.method == 'POST' and 'l_grado' in request.POST:
		grado = request.POST['l_grado']
		# Confirmaciones
		if 'actions' in request.POST and 'all_alumnos' in request.POST:
			alumnos = request.POST.getlist('all_alumnos')
			l_alumnos = []
			for alumno in alumnos:
				l_alumnos.append(ldap_search(settings.LDAP_STUDENTS_BASE,ldap.SCOPE_SUBTREE,None,"(uid="+alumno+")"))
			if request.POST['actions'] == 'baja_selected':
				return render(request, 'pgdiapp/confirmar_baja_multiple.html', { 'alumnos': l_alumnos, 'grado':grado })
		# Bajas
		if 'bajas' in request.POST and int(request.POST['bajas']) > 0:
			alumnos = request.POST.getlist('all_alumnos')
			for alumno in alumnos:
				baja_efectiva(grado, alumno)
			return render(request, 'pgdiapp/bajas.html', { 'grado':grado })
	else:
		grado = l_grados[0]
		try:
			for g in l_grados:
				if g in request.META['HTTP_REFERER']:
					grado = g
		except:
			pass
	# Mostrar listado 
	alumnos = ldap_search("ou="+grado+","+settings.LDAP_STUDENTS_BASE,ldap.SCOPE_ONELEVEL,None,"(objectClass=posixAccount)")
	return render(request, 'pgdiapp/alumnos.html', { 'alumnos': alumnos, 'grado':grado, 'l_grados':l_grados })

# Listado de alumnos registrados (no validados)
def pendientes(request):
	try:
		grupos = request.user.ldap_user.group_names
	except:
		return redirect('/app/login')
	l_grados = obtener_grados(grupos)
	# Operaciones múltiples
	if request.method == 'POST' and 'l_grado' in request.POST:
		grado = request.POST['l_grado']
		# Confirmaciones
		if 'actions' in request.POST and 'all_alumnos' in request.POST:
			alumnos = request.POST.getlist('all_alumnos')
			l_alumnos = []
			for alumno in alumnos:
				l_alumnos.append(Perfil.objects.get(grado__cod=grado,user__username=alumno,validado=False))
			if request.POST['actions'] == 'alta_selected':
				return render(request, 'pgdiapp/confirmar_alta_multiple.html', { 'alumnos': l_alumnos, 'grado':grado })
			if request.POST['actions'] == 'descartar_selected':
				return render(request, 'pgdiapp/confirmar_descarte_multiple.html', { 'alumnos': l_alumnos, 'grado':grado })
		# Altas
		if 'altas' in request.POST and int(request.POST['altas']) > 0:
			alumnos = request.POST.getlist('all_alumnos')
			for alumno in alumnos:
				alta_efectiva(grado, alumno)
			return render(request, 'pgdiapp/altas.html', { 'grado':grado })
		# Descartes
		if 'descartes' in request.POST and int(request.POST['descartes']) > 0:
			alumnos = request.POST.getlist('all_alumnos')
			for alumno in alumnos:
				descarte_efectivo(grado, alumno)
			return render(request, 'pgdiapp/descartes.html', { 'grado':grado })
	else:
		grado = l_grados[0]
		try:
			for g in l_grados:
				if g in request.META['HTTP_REFERER']:
					grado = g
		except:
			pass
	# Mostrar listado 
	alumnos = Perfil.objects.filter(grado__cod=grado,validado=False)
	return render(request, 'pgdiapp/pendientes.html', { 'alumnos': alumnos, 'grado':grado, 'l_grados':l_grados })

# Entrada al perfil
def perfil(request, grado, usuario):
	alumno = ldap_search("ou="+grado+","+settings.LDAP_STUDENTS_BASE,ldap.SCOPE_ONELEVEL,None,"(uid="+usuario+")")
	if len(alumno) != 1:
		return redirect('/app')
	# Obtener foto
	if 'jpegPhoto' in alumno[0][0][1]:
		alumno[0][0][1]['jpegPhoto'][0] = base64.b64encode(bytes(alumno[0][0][1]['jpegPhoto'][0]))
	# Obtener mensajes de ayuda
	if request.user.is_authenticated and not request.user.is_staff:
		l_grado = Perfil.objects.get(user=request.user).grado
		portada = Portada.objects.filter(grado=l_grado,visible=True)
	else:
		portada = None
	# Obtener quotas y espacio ocupado en disco
	hd = alumno[0][0][1]['homeDirectory'][0]
	usado, blando, duro = consultar_cuota(usuario)
	top = consultar_mas_pesados(usuario,hd,settings.MAX_SIZE_FILE_LIMIT)
	try:
		p = float(usado) / float(blando) * float(100)
	except:
		p = 0
	porcentaje = float("{0:.2f}".format(p))
	return render( 
		request, 'pgdiapp/perfil.html', 
		{ 
			'alumno': alumno, 'grado':grado, 'portada':portada,
			'cuota':humanizar(int(usado)), 'blando':humanizar(int(blando)), 'duro':humanizar(int(duro)), 
			'porcentaje':porcentaje, 'top':top, 'w1':settings.QUOTA_WARN1_LEVEL ,'w2':settings.QUOTA_WARN2_LEVEL 
		}
	)

# Edición de perfil
def editar(request, grado, usuario):
	alumno = ldap_search("ou="+grado+","+settings.LDAP_STUDENTS_BASE,ldap.SCOPE_ONELEVEL,None,"(uid="+usuario+")")
	if len(alumno) != 1:
		return redirect('/app')
	if request.method == 'POST':
		pform = UserProfileMiniForm(data = request.POST)
		if pform.is_valid():
			perfil = Perfil.objects.get(user__username=usuario)
			perfil.telefono = request.POST['telefono']
			perfil.email = request.POST['email']
			perfil.cp = request.POST['cp']
			perfil.direccion = request.POST['direccion']
			perfil.localidad = request.POST['localidad']
			perfil.provincia = request.POST['provincia']
			perfil.comunidad = request.POST['comunidad']
			perfil.pais = request.POST['pais']
			# Sincronizar con ldap
			sincronizar(usuario,grado,perfil.telefono,perfil.email,perfil.cp,perfil.direccion,perfil.localidad,perfil.provincia,perfil.comunidad,perfil.pais)
			# Actualizar el modelo
			perfil.save()
			return HttpResponseRedirect("/app/perfil/"+grado+"/"+usuario)
	else:
		pform = UserProfileMiniForm()
	return render(request, 'pgdiapp/edicion_perfil.html', { 'alumno': alumno, 'grado':grado, 'pform':pform })

# Subir foto de perfil
def subir_foto(request, grado, usuario):
	if request.method == 'POST':
		form = PhotoForm(request.POST, request.FILES)
		if form.is_valid():
			if validar_foto(request.FILES['photo']):
				actualizar_foto(usuario, grado, request.FILES['photo'])
				return HttpResponseRedirect("/app/perfil/"+grado+"/"+usuario)
			else:
				return HttpResponseRedirect("/app/formatonovalido")
	else:
		form = PhotoForm()
	return render(request, 'pgdiapp/subir_foto.html', { 'alumno': usuario, 'grado':grado, 'form': form })

# Respuestas del cuestionario
def respuestas(request, grado, usuario):
	try:
		alumno = Perfil.objects.get(user__username=usuario)
		respuestas = Respuesta.objects.filter(alumno=alumno)
	except:
		alumno = None
		respuestas = None
	return render(request, 'pgdiapp/respuestas.html', { 'alumno': alumno, 'respuestas':respuestas })

# Pre-registro de un nuevo alumno
def registro(request):
	ip = request.META['REMOTE_ADDR']
	hora = datetime.now().strftime('%H')
	grado = obtener_grado(ip, hora)
	freeun = Configuracion.objects.get(clave='freeusername').valor
	openrg = Configuracion.objects.get(clave='openregister').valor
	if request.method == 'POST':
		myPass = encriptar(request.POST['password1'])
		uform = UserCreationForm(request.POST)
		pform = UserProfileForm(data = request.POST)
		if uform.is_valid() and pform.is_valid():
			user = uform.save(commit = False)
			profile = pform.save(commit = False)
			if not freeun:
				user.username = generar_username(profile.nombre,profile.apellido1,profile.apellido2)
			user.save()
			profile.user = user
			profile.dni = profile.dni.upper()
			profile.passwd = myPass
			profile.save()
			return HttpResponseRedirect("/app/cuestionario/"+str(user.username))
	else:
		uform = UserCreationForm()
		pform = UserProfileForm()
	return render(request, 'pgdiapp/user_form.html', { 'uform': uform, 'pform': pform, 'grado':grado, 'ip':ip, 'freeun':freeun, 'openrg':openrg })

# Pre-registro de un antiguo alumno
def regreso(request):
	ip = request.META['REMOTE_ADDR']
	dni = None
	hora = datetime.now().strftime('%H')
	grado = obtener_grado(ip, hora)
	openrg = Configuracion.objects.get(clave='openregister').valor
	usuario = None
	l_grados = Grado.objects.all()
	if request.method == 'POST':
		if request.POST['dni'] and request.POST['grado']:
			if "acerca de" in request.POST['dni'].lower():
				return render(request, 'pgdiapp/ee.html')
			else:
				l_usuarios = ldap_search(settings.LDAP_EXSTUDENTS_BASE,ldap.SCOPE_ONELEVEL,None,"(dni="+request.POST['dni']+")")
				if len(l_usuarios) == 1:
					usuario = l_usuarios[0][0][1]['uid'][0]
					grado = request.POST['grado']
					perfil = Perfil.objects.get(user__username=usuario)
					objGrado = Grado.objects.get(cod=grado)
					if not perfil.grado:
						perfil.grado = objGrado
						perfil.save()
						return HttpResponseRedirect("/app/cuestionario/"+str(usuario))
					else:
						return HttpResponseRedirect("/app/noencontrado")
				else:
					return HttpResponseRedirect("/app/noencontrado")
	return render(request, 'pgdiapp/old_user_form.html', { 'dni':dni, 'l_grados':l_grados, 'grado':grado, 'ip':ip, 'openrg':openrg })

# Formulario de preguntas
def cuestionario(request, user_name):
	usuario = User.objects.get(username=user_name)
	perfil = Perfil.objects.get(user=usuario)
	preguntas = Cuestionario.objects.filter(grado=perfil.grado)
	RespuestaFormSet = formset_factory(RespuestaForm, extra=len(preguntas))
	openrg = Configuracion.objects.get(clave='openregister').valor
	if len(Respuesta.objects.filter(alumno=perfil)) > 0:
		openrg = False
	if request.method == 'POST':
		respuestas = RespuestaFormSet(request.POST)
		if respuestas.is_valid():
			for respuesta in respuestas:
				respuesta.save()
			return render(request, 'pgdiapp/registro_completo.html', { 'alumno': perfil })
	else:
		respuestas = RespuestaFormSet()
	return render(request, 'pgdiapp/cuestionario.html', { 'alumno':perfil, 'preguntas':preguntas, 'respuestas':RespuestaFormSet, 'openrg':openrg })

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
			try:
				return HttpResponseRedirect("/app/perfil/"+perfil.grado.cod+"/"+username)
			except:
				logout(request)
				return redirect('/app/error')
		else:
			return redirect('/app/error')
	else:
		return render(request, 'pgdiapp/login.html')

# Cambiar contraseña
def chpasswd(request):
	if request.method == 'POST':
		form = PasswordChangeForm(request.user, request.POST)
		if form.is_valid():
			user = form.save()
			myPass = encriptar(request.POST['new_password1'])
			profile = Perfil.objects.get(user=user)
			sync_pass(profile.user.username,profile.grado.cod,profile.passwd,myPass)
			profile.passwd = myPass
			profile.save()
			update_session_auth_hash(request, user)
			logout(request)
			return HttpResponseRedirect("/app/chpasswd_redirect")
	else:
		form = PasswordChangeForm(request.user)
	return render(request, 'pgdiapp/pw_change.html', { 'form': form })

def sync_pass(alumno,grado,old_pass,new_pass):
	l = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
	l.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)
	dn="cn="+alumno+",ou="+grado+","+settings.LDAP_STUDENTS_BASE
	old = {'userPassword':old_pass.encode('utf-8')}
	new = {'userPassword':new_pass.encode('utf-8')}
	ldif = modlist.modifyModlist(old,new)
	l.modify_s(dn,ldif)
	l.unbind_s()

def chpasswdr(request):
	return render(request, 'pgdiapp/password_ok.html')

# Logout
def logout_view(request):
	logout(request)
	return redirect('/app/logout_redirect')

def logoutr(request):
	return render(request, 'pgdiapp/logout.html')

# Vistas de error
def error(request):
	return render(request, 'pgdiapp/error.html')

def noencontrado(request):
	return render(request, 'pgdiapp/noencontrado.html')

def formatonovalido(request):
	return render(request, 'pgdiapp/formatonovalido.html')
