#-*- coding: utf-8 -*-

from django.conf import settings

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from lxml.html.clean import clean_html

from .forms import *
from .models import *

import ldap, copy, crypt, string, random, unicodedata, base64, smtplib, subprocess
import ldap.modlist as modlist

from utiles import *

# Consultar cuotas de disco
def consultar_cuota(usuario):
	proceso = subprocess.Popen(["ssh", "-p" + str(settings.SSH_PORT), "-i" + str(settings.SSH_KEY_REPQUOTA), settings.SSH_USER + "@" + settings.SSH_HOST], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
	salida = proceso.stdout.readlines()
	if salida == []:
		error = proceso.stderr.readlines()
	else:
		for linea in salida:
			if usuario in linea:
				cuota = linea
	try:
		cuota = cuota.split(',')
	except:
		return (0,0,0)
	return (cuota[settings.QUOTA_USED_DISK_FIELD],cuota[settings.QUOTA_SOFT_LIMIT_FIELD],cuota[settings.QUOTA_HARD_LIMIT_FIELD])

# Consultar ficheros más pesados
def consultar_mas_pesados(usuario,n=None):
	parametros = str(settings.HOME_DIRECTORY + usuario) + '/*'
	proceso = subprocess.Popen(["ssh", "-p" + str(settings.SSH_PORT), "-i" + str(settings.SSH_KEY_DU), settings.SSH_USER + "@" + settings.SSH_HOST, parametros], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
	s1 = proceso.stdout.readlines()
	parametros = str(settings.HOME_DIRECTORY + usuario) + '/.[!.]*'
	proceso = subprocess.Popen(["ssh", "-p" + str(settings.SSH_PORT), "-i" + str(settings.SSH_KEY_DU), settings.SSH_USER + "@" + settings.SSH_HOST, parametros], stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
	s2 = proceso.stdout.readlines()
	salida = s1 + s2
	if salida == []:
		error = proceso.stderr.readlines()
		return [["INFO:","El directorio " + str(settings.HOME_DIRECTORY + usuario) + " no existe o esta vacío."]]
	else:
		listado = []
		for linea in salida:
			listado.append(linea.split('\t'))
			listado[-1][0] = int(listado[-1][0])
			listado[-1][1] = listado[-1][1].replace(str(settings.HOME_DIRECTORY + usuario),"~")
		listado.sort(reverse=True)
		if n:
			while (len(listado) > n):
				listado.pop(-1)
		for idx in range(0,len(listado)):
			listado[idx][0] = humanizar(listado[idx][0])
		return listado
