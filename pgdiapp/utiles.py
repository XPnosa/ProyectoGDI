#-*- coding: utf-8 -*-

from django.conf import settings
from django.shortcuts import render, redirect, render_to_response 
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest

from .forms import *
from .models import *

import ldap, copy, crypt, string, random, unicodedata, base64, smtplib, subprocess
import ldap.modlist as modlist

from correos import *

# Encriptar la contraseña
def encriptar(plano):
	encriptado = "{CRYPT}"+crypt.crypt(plano,'$6$'+"".join([random.choice(string.ascii_letters+string.digits) for _ in range(16)]))
	return encriptado

# Habilitar/Deshabilitar el registro
def regmod(request):
	if request.user.is_staff:
		openrg = Configuracion.objects.get(clave='openregister')
		if openrg.valor:
			openrg.valor = False
		else:
			openrg.valor = True
		openrg.save()
	return redirect('/app')

# Habilitar/Deshabilitar la elección del nombre de usuario
def funmod(request):
	if request.user.is_staff:
		freeun = Configuracion.objects.get(clave='freeusername')
		if freeun.valor:
			freeun.valor = False
		else:
			freeun.valor = True
		freeun.save()
	return redirect('/app')

# Obtención de la lista de grados del profesor
def obtener_grados(grupos):
	l_grados = []
	if 'ASIR' in grupos:
		l_grados.append('ASIR')
	if 'DAM' in grupos:
		l_grados.append('DAM')
	if 'SMR' in grupos:
		l_grados.append('SMR')
	return l_grados

# Obtención del grado por taller
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

# Generación del nombre del usuario
def generar_username(nom, ap1, ap2):
	for character in string.digits+" @.+-_":
		nom = nom.replace(character,'')
		ap1 = ap1.replace(character,'')
		ap2 = ap2.replace(character,'')
	return ''.join((c for c in unicodedata.normalize('NFD', (nom+ap1[:2]+ap2[:2]).lower()) if unicodedata.category(c) != 'Mn'))

# Cálculo de un nuevo uid/gid number
def calcular_id(xid):
	usuarios = ldap_search(settings.LDAP_USERS_BASE,ldap.SCOPE_SUBTREE,None,"(objectClass=person)")
	ids = []
	for u in usuarios:
		ids.append(int(u[0][1][xid][0]))
	return max(ids)+1

# Comprobación de antiguos alumnos
def es_exalumno(usuario):
	if len(ldap_search(settings.LDAP_EXSTUDENTS_BASE,ldap.SCOPE_ONELEVEL,None,"(uid="+usuario+")")) > 0:
		esExalumno = True
	else:
		esExalumno = False
	return esExalumno

# Convertir a formato humano tamaños de ficheros
def humanizar(nb):
	sufijo = ['K', 'M', 'G', 'T', 'P']
	if nb == 0: return '0K'
	i = 0
	while nb >= 1024 and i < len(sufijo)-1:
		nb /= 1024
		i += 1
	return '%s%s' % (nb, sufijo[i])

# Validar foto de perfil
def validar_foto(foto):
	if foto.content_type == "image/jpeg" and foto.size <= 1024*1024:
		return True
	return False

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

# Búsqueda de datos en ldap
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
