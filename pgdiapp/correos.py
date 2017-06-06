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

# Envío de emails
def construir_correo(usuario, grado, tipo):
	objMsg = Mensaje.objects.get(cod=tipo)
	origen = settings.SMTP_NAME
	destino = usuario.email
	msg = MIMEMultipart()
	msg['To'] = destino
	msg['From'] = origen
	msg['Subject'] = objMsg.asunto
	mensaje = expandir_etiquetas(clean_html(objMsg.cuerpo),usuario.user.username,grado)
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
