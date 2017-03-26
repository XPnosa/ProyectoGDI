from django import forms
from .models import Perfil, Respuesta

class UserProfileForm(forms.ModelForm):
	class Meta:
		model = Perfil
		fields = ["nombre","apellido1","apellido2","telefono","email","modulo","fecha_nac"]

class RespuestaForm(forms.ModelForm):
	class Meta:
		model = Respuesta
		fields = ["alumno","r1","r2","r3","r4","r5","r6","r7","r8","r9",]
