from django.shortcuts import render, redirect, render_to_response 
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.views.generic.edit import CreateView, UpdateView, DeleteView
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django_auth_ldap.config import LDAPSearch, PosixGroupType
from django.conf import settings

from .forms import UserProfileForm, RespuestaForm
from .models import *

from datetime import datetime

import ldap, copy, crypt, string, random, unicodedata
import ldap.modlist as modlist

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

# Listado de alumnos registrados (no validados)
def pendientes(request):
	try:
		grupos = request.user.ldap_user.group_names
	except:
		return redirect('/app/login')
	l_grados = obtener_grados(grupos)
	if request.method == 'POST':
		grado = request.POST['l_grado']
	else:
		grado = l_grados[0]
		try:
			for g in l_grados:
				if g in request.META['HTTP_REFERER']:
					grado = g
		except:
			pass
	alumnos = Perfil.objects.filter(grado__cod=grado,validado=False)
	return render(request, 'pgdiapp/pendientes.html', { 'alumnos': alumnos, 'grado':grado, 'l_grados':l_grados })

# Listado de alumnos validados
def alumnos(request):
	try:
		grupos = request.user.ldap_user.group_names
	except:
		return redirect('/app/login')
	l_grados = obtener_grados(grupos)
	if request.method == 'POST':
		grado = request.POST['l_grado']
	else:
		grado = l_grados[0]
		try:
			for g in l_grados:
				if g in request.META['HTTP_REFERER']:
					grado = g
		except:
			pass
	alumnos = ldap_search("ou="+grado+","+settings.LDAP_STUDENTS_BASE,ldap.SCOPE_ONELEVEL,None,"(objectClass=posixAccount)")
	return render(request, 'pgdiapp/alumnos.html', { 'alumnos': alumnos, 'grado':grado, 'l_grados':l_grados })

# Entrada al perfil
def perfil(request, grado, usuario):
	alumno = ldap_search(settings.LDAP_STUDENTS_BASE,ldap.SCOPE_SUBTREE,None,"(uid="+usuario+")")
	return render(request, 'pgdiapp/perfil.html', { 'alumno': alumno, 'grado':grado })

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
			profile.passwd = myPass
			profile.save()
			return HttpResponseRedirect("/app/cuestionario/"+str(user.username))
	else:
		uform = UserCreationForm()
		pform = UserProfileForm()
	return render(request, 'pgdiapp/user_form.html', { 'uform': uform, 'pform': pform, 'grado':grado, 'ip':ip, 'freeun':freeun, 'openrg':openrg })

# Pre-registro de un nuevo alumno
def regreso(request):
	ip = request.META['REMOTE_ADDR']
	hora = datetime.now().strftime('%H')
	grado = obtener_grado(ip, hora)
	openrg = Configuracion.objects.get(clave='openregister').valor
	l_usuarios = ldap_search(settings.LDAP_EXSTUDENTS_BASE,ldap.SCOPE_ONELEVEL,None,"(objectClass=posixAccount)")
	l_grados = Grado.objects.all()
	if request.method == 'POST':
		usuario = request.POST['username']
		grado = request.POST['grado']
		perfil = Perfil.objects.get(user__username=usuario)
		objGrado = Grado.objects.get(cod=grado)
		perfil.grado = objGrado
		perfil.save()
		return HttpResponseRedirect("/app/cuestionario/"+str(usuario))
	return render(request, 'pgdiapp/old_user_form.html', { 'l_usuarios':l_usuarios, 'l_grados':l_grados, 'grado':grado, 'ip':ip, 'openrg':openrg })

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

# Funcion para encriptar
def encriptar(plano):
	encriptado = "{CRYPT}"+crypt.crypt(plano,'$6$'+"".join([random.choice(string.ascii_letters+string.digits) for _ in range(16)]))
	return encriptado

# Obtencion de la lista de grados del profesor
def obtener_grados(grupos):
	l_grados = []
	if 'ASIR' in grupos:
		l_grados.append('ASIR')
	if 'DAM' in grupos:
		l_grados.append('DAM')
	if 'SMR' in grupos:
		l_grados.append('SMR')
	return l_grados

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
	for character in string.digits+" @.+-_":
		nom = nom.replace(character,'')
		ap1 = ap1.replace(character,'')
		ap2 = ap2.replace(character,'')
	return ''.join((c for c in unicodedata.normalize('NFD', (nom+ap1[:2]+ap2[:2]).lower()) if unicodedata.category(c) != 'Mn'))

# Calculo de un nuevo uid/gid number
def calcular_id(xid):
	usuarios = ldap_search(settings.LDAP_USERS_BASE,ldap.SCOPE_SUBTREE,None,"(objectClass=person)")
	ids = []
	for u in usuarios:
		ids.append(int(u[0][1][xid][0]))
	return max(ids)+1

# Comprobacion de antiguos alumnos
def es_exalumno(usuario):
	if len(ldap_search(settings.LDAP_EXSTUDENTS_BASE,ldap.SCOPE_ONELEVEL,None,"(uid="+usuario+")")) > 0:
		esExalumno = True
	else:
		esExalumno = False
	return esExalumno

# Busqueda de datos en ldap
def ldap_search(baseDN,searchScope,retrieveAttributes,searchFilter):
	l = ldap.open(settings.LDAP_SERVER_NAME)
	l.protocol_version = settings.LDAP_VERSION
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

# Dar de alta un alumno
def alta(request, grado, usuario):
	alumno = Perfil.objects.get(user__username=usuario)
	l = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
	l.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)

	if es_exalumno(usuario):
		# Mover desde exalumnos en ldap
		l.rename_s("cn="+usuario+","+settings.LDAP_EXSTUDENTS_BASE, "cn="+usuario, "ou="+grado+","+settings.LDAP_STUDENTS_BASE)
	else:
		# Crear usuario en ldap
		attrs = {}
		attrs['objectclass'] = ['posixAccount','inetOrgPerson','organizationalPerson','person','pgdi','top']
		attrs['cn'] = str(alumno.user.username)
		attrs['uid'] = str(alumno.user.username)
		attrs['givenName'] = str(alumno.nombre)
		attrs['sn'] = str(alumno.apellido1+" "+alumno.apellido2)
		attrs['mail'] = str(alumno.email)
		attrs['telephoneNumber'] = str(alumno.telefono)
		attrs['fnac'] = str(alumno.fecha_nac).replace('-','')+'000000Z'
		attrs['dni'] = str(alumno.dni)
		attrs['loginShell'] = '/bin/bash'
		attrs['homeDirectory'] = str('/home/pub/'+alumno.user.username)
		attrs['uidNumber'] = str(calcular_id('uidNumber'))
		attrs['gidNumber'] = str(calcular_id('gidNumber'))
		attrs['userPassword'] = str(alumno.passwd)

		dn="cn="+usuario+",ou="+grado+","+settings.LDAP_STUDENTS_BASE
		ldif = modlist.addModlist(attrs)
		l.add_s(dn,ldif)

	# Agregar a grupos en ldap
	old = {}
	new = {'memberUid':str(alumno.user.username)}

	dn="cn=alumnos,"+settings.LDAP_ROLES_BASE
	ldif = modlist.modifyModlist(old,new)
	l.modify_s(dn,ldif)

	dn="cn="+grado+","+settings.LDAP_GRADES_BASE
	ldif = modlist.modifyModlist(old,new)
	l.modify_s(dn,ldif)

	dn="cn=activos,"+settings.LDAP_ROLES_BASE
	ldif = modlist.modifyModlist(old,new)
	l.modify_s(dn,ldif)

	for grp in Grupo.objects.all():
		try:
			dn=grp.dn
			ldif = modlist.modifyModlist(old,new)
			l.modify_s(dn,ldif)
		except:
			pass

	l.unbind_s()

	# Actualizar perfil temporal
	alumno.validado = True
	alumno.save()
	return render(request, 'pgdiapp/alta.html', { 'alumno': alumno })

# Dar de baja un alumno
def confirmar_baja(request, grado, usuario):
	alumno = ldap_search(settings.LDAP_STUDENTS_BASE,ldap.SCOPE_SUBTREE,None,"(uid="+usuario+")")
	return render(request, 'pgdiapp/confirmar_baja.html', { 'alumno': alumno, 'grado':grado })

def baja(request, grado, usuario):
	l = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
	l.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)

	# Mover a exalumnos en ldap
	l.rename_s("cn="+usuario+",ou="+grado+","+settings.LDAP_STUDENTS_BASE, "cn="+usuario, settings.LDAP_EXSTUDENTS_BASE)

	# Eliminar de grupos en ldap
	dn="cn=alumnos,"+settings.LDAP_ROLES_BASE
	old = ldap_search(dn,ldap.SCOPE_BASE,None,"(objectClass=posixGroup)")[0][0][1]
	new = copy.deepcopy(old)
	new['memberUid'].remove(usuario)
	ldif = modlist.modifyModlist(old,new)
	l.modify_s(dn,ldif)

	dn="cn="+grado+","+settings.LDAP_GRADES_BASE
	old = ldap_search(dn,ldap.SCOPE_BASE,None,"(objectClass=posixGroup)")[0][0][1]
	new = copy.deepcopy(old)
	new['memberUid'].remove(usuario)
	ldif = modlist.modifyModlist(old,new)
	l.modify_s(dn,ldif)

	dn="cn=activos,"+settings.LDAP_ROLES_BASE
	old = ldap_search(dn,ldap.SCOPE_BASE,None,"(objectClass=posixGroup)")[0][0][1]
	new = copy.deepcopy(old)
	new['memberUid'].remove(usuario)
	ldif = modlist.modifyModlist(old,new)
	l.modify_s(dn,ldif)

	for grp in Grupo.objects.all():
		try:
			dn=grp.dn
			old = ldap_search(dn,ldap.SCOPE_BASE,None,"(objectClass=posixGroup)")[0][0][1]
			new = copy.deepcopy(old)
			new['memberUid'].remove(usuario)
			ldif = modlist.modifyModlist(old,new)
			l.modify_s(dn,ldif)
		except:
			pass

	l.unbind_s()

	# Actualizar perfil temporal
	exalumno = Perfil.objects.get(user__username=usuario)
	respuestas = Respuesta.objects.filter(alumno=exalumno)
	for respuesta in respuestas:
		respuesta.delete()
	exalumno.grado = None
	exalumno.validado = False
	exalumno.save()
	return render(request, 'pgdiapp/baja.html')

# Descartar alumnos pre-registrados
def confirmar_descarte(request, grado, usuario):
	return render(request, 'pgdiapp/confirmar_descarte.html', { 'alumno': usuario, 'grado':grado })

def descarte(request, grado, usuario):
	alumno = User.objects.get(username=usuario)
	if es_exalumno(usuario):
		alumno = Perfil.objects.get(user__username=usuario)
		alumno.grado = None
		alumno.save()
	else:
		alumno = User.objects.get(username=usuario)
		alumno.delete()
	return render(request, 'pgdiapp/descarte.html', { 'alumno': usuario, 'grado':grado })

# Dar de alta a un antiguo alumno
def chgrado(request):
	return redirect('/app')

# Cambiar password (TODO)
def chpasswd(request):
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
