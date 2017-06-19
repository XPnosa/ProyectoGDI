#-*- coding: utf-8 -*-

from django.conf import settings
from django.shortcuts import render, redirect, render_to_response 
from django.http import HttpResponse, HttpResponseRedirect, HttpRequest

from .forms import *
from .models import *

from utiles import *

# Dar de baja alumnos
def confirmar_baja(request, grado, usuario):
	if request.user.is_staff:
		alumno = ldap_search(settings.LDAP_STUDENTS_BASE,ldap.SCOPE_SUBTREE,None,"(uid="+usuario+")")
		return render(request, 'pgdiapp/confirmar_baja.html', { 'alumno': alumno, 'grado':grado })

def baja(request, grado, usuario):
	if request.user.is_staff:
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
	try:
		exalumno = Perfil.objects.get(user__username=usuario)
		respuestas = Respuesta.objects.filter(alumno=exalumno)
		for respuesta in respuestas:
			respuesta.delete()
		exalumno.grado = None
		exalumno.validado = False
		exalumno.save()
	except:
		pass
	# Envíar correo de despedida
	construir_correo(exalumno,grado,'BYEBYE')
