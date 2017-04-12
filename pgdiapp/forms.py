from django import forms
from .models import Perfil, Respuesta

class UserProfileForm(forms.ModelForm):
	class Meta:
		model = Perfil
		fields = ["dni","nombre","apellido1","apellido2","telefono","email","grado","fecha_nac","cp","direccion","localidad","provincia","comunidad","pais"]


class UserProfileMiniForm(forms.ModelForm):
	class Meta:
		model = Perfil
		fields = ["telefono","email","cp","direccion","localidad","provincia","comunidad","pais"]


class RespuestaForm(forms.ModelForm):
	class Meta:
		model = Respuesta
		fields = ["alumno","pregunta","texto"]
