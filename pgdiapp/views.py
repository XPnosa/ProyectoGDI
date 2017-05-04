from django.shortcuts import render, redirect, render_to_response 
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest
from django.contrib.auth.forms import UserCreationForm, PasswordChangeForm
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.forms import formset_factory
from django_auth_ldap.config import LDAPSearch, PosixGroupType
from django.conf import settings

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from datetime import datetime

from .forms import *
from .models import *

import ldap, copy, crypt, string, random, unicodedata, base64, smtplib
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
	# Operaciones multiples
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

# Listado de alumnos validados
def alumnos(request):
	try:
		grupos = request.user.ldap_user.group_names
	except:
		return redirect('/app/login')
	l_grados = obtener_grados(grupos)
	# Operaciones multiples
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

# Entrada al perfil
def perfil(request, grado, usuario):
	alumno = ldap_search("ou="+grado+","+settings.LDAP_STUDENTS_BASE,ldap.SCOPE_ONELEVEL,None,"(uid="+usuario+")")
	if len(alumno) != 1:
		return redirect('/app')
	if 'jpegPhoto' in alumno[0][0][1]:
		alumno[0][0][1]['jpegPhoto'][0] = base64.b64encode(bytes(alumno[0][0][1]['jpegPhoto'][0]))
	return render(request, 'pgdiapp/perfil.html', { 'alumno': alumno, 'grado':grado })

# Edicion de perfil
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

# Validar foto de perfil
def validar_foto(foto):
	if foto.content_type == "image/jpeg" and foto.size <= 1024*1024:
		return True
	return False

# Sincronizar perfil en ldap
def sincronizar(alumno,grado,telefono,email,cp,direccion,localidad,provincia,comunidad,pais):
	l = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
	l.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)
	dn="cn="+alumno+",ou="+grado+","+settings.LDAP_STUDENTS_BASE
	old = ldap_search(dn,ldap.SCOPE_BASE,None,"(cn="+alumno+")")[0][0][1]
	new = copy.deepcopy(old)
	new['telephoneNumber'] = telefono.encode('utf-8')
	new['mail'] = email.encode('utf-8')
	new['postalCode'] = cp.encode('utf-8')
	new['street'] = direccion.encode('utf-8')
	new['l'] = localidad.encode('utf-8')
	new['st'] = provincia.encode('utf-8')
	new['c'] = comunidad.encode('utf-8')
	new['co'] = pais.encode('utf-8')
	ldif = modlist.modifyModlist(old,new)
	l.modify_s(dn,ldif)
	l.unbind_s()

# Actualizar foto de perfil en ldap
def actualizar_foto(alumno,grado,foto):
	l = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
	l.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)
	dn="cn="+alumno+",ou="+grado+","+settings.LDAP_STUDENTS_BASE
	old = ldap_search(dn,ldap.SCOPE_BASE,None,"(cn="+alumno+")")[0][0][1]
	new = copy.deepcopy(old)
	new['jpegPhoto'] = foto.read()
	ldif = modlist.modifyModlist(old,new)
	l.modify_s(dn,ldif)
	l.unbind_s()

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

# Pre-registro de un nuevo alumno
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

# Formularo de preguntas
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

# Dar de alta alumnos
def alta(request, grado, usuario):
	alumno = alta_efectiva(grado, usuario)
	return render(request, 'pgdiapp/alta.html', { 'alumno': alumno })

def alta_efectiva(grado, usuario):
	alumno = Perfil.objects.get(user__username=usuario)
	l = ldap.initialize(settings.AUTH_LDAP_SERVER_URI)
	l.simple_bind_s(settings.AUTH_LDAP_BIND_DN,settings.AUTH_LDAP_BIND_PASSWORD)

	if es_exalumno(usuario):
		# Mover desde exalumnos en ldap
		l.rename_s("cn="+usuario+","+settings.LDAP_EXSTUDENTS_BASE, "cn="+usuario, "ou="+grado+","+settings.LDAP_STUDENTS_BASE)
	else:
		# Crear usuario en ldap
		attrs = {}
		attrs['objectclass'] = ['posixAccount','inetOrgPerson','person','extensibleObject','pgdi','top']
		attrs['cn'] = str(alumno.user.username)
		attrs['uid'] = str(alumno.user.username)
		attrs['givenName'] = alumno.nombre.encode('utf-8')
		attrs['sn'] = (alumno.apellido1+" "+alumno.apellido2).encode('utf-8')
		attrs['mail'] = alumno.email.encode('utf-8')
		attrs['telephoneNumber'] = str(alumno.telefono)
		attrs['fnac'] = str(alumno.fecha_nac).replace('-','')+'000000Z'
		attrs['dni'] = str(alumno.dni)
		attrs['postalCode'] = str(alumno.cp)
		attrs['street'] = alumno.direccion.encode('utf-8')
		attrs['l'] = alumno.localidad.encode('utf-8')
		attrs['st'] = alumno.provincia.encode('utf-8')
		attrs['c'] = alumno.comunidad.encode('utf-8')
		attrs['co'] = alumno.pais.encode('utf-8')
		attrs['loginShell'] = str(settings.LOGIN_SHELL)
		attrs['homeDirectory'] = str(settings.HOME_DIRECTORY+alumno.user.username)
		attrs['uidNumber'] = str(calcular_id('uidNumber'))
		attrs['gidNumber'] = str(calcular_id('gidNumber'))
		attrs['quota'] = str(settings.MAX_STORAGE_QUOTA)
		attrs['userPassword'] = alumno.passwd.encode('utf-8')

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

	for grp in Grupo.objects.filter(grado__cod=grado):
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
	# Enviar correo de bienvenida
	construir_correo(alumno,grado,'WELCOME')
	return alumno

# Dar de baja alumnos
def confirmar_baja(request, grado, usuario):
	alumno = ldap_search(settings.LDAP_STUDENTS_BASE,ldap.SCOPE_SUBTREE,None,"(uid="+usuario+")")
	return render(request, 'pgdiapp/confirmar_baja.html', { 'alumno': alumno, 'grado':grado })

def baja(request, grado, usuario):
	baja_efectiva(grado, usuario)
	return render(request, 'pgdiapp/baja.html')

def baja_efectiva(grado, usuario):
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

	for grp in Grupo.objects.filter(grado__cod=grado):
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
	# Enviar correo de despedida
	construir_correo(exalumno,grado,'BYEBYE')

# Descartar alumnos pre-registrados
def confirmar_descarte(request, grado, usuario):
	return render(request, 'pgdiapp/confirmar_descarte.html', { 'alumno': usuario, 'grado':grado })

def descarte(request, grado, usuario):
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

# Envio de emails
def construir_correo(usuario, grado, tipo):
	objMsg = Mensaje.objects.get(cod=tipo)
	origen = settings.SMTP_NAME
	destino = usuario.email
	msg = MIMEMultipart()
	msg['To'] = destino
	msg['From'] = origen
	msg['Subject'] = objMsg.asunto
	mensaje = expandir_etiquetas(objMsg.cuerpo,usuario.user.username,grado)
	msg.attach(MIMEText(mensaje,'html'))
	enviar_correo(origen,destino,msg)

def expandir_etiquetas(mensaje,usuario,grado):
	mensaje = mensaje.replace('{{USUARIO}}',usuario)
	mensaje = mensaje.replace('{{GRADO}}',grado)
	return mensaje

def enviar_correo(origen,destino,msg):
	try:
		server = smtplib.SMTP(settings.SMTP_HOST)
		server.starttls()
		server.login(settings.SMTP_USER,settings.SMTP_PASS)
		server.sendmail(origen, destino, msg.as_string())
		server.quit()
	except:
		pass

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

# Cambiar password
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
