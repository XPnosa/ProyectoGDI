from django import forms
from .models import Perfil, Respuesta
from django.contrib.admin.widgets import AdminDateWidget 

class UserProfileForm(forms.ModelForm):
	class Meta:
		model = Perfil
		fields = ["dni","nombre","apellido1","apellido2","telefono","email","grado","fecha_nac","cp","direccion","localidad","provincia","comunidad","pais"]
		widgets = {
			'fecha_nac': forms.DateInput(attrs={'type': 'date'}),
		}

class UserProfileMiniForm(forms.ModelForm):
	class Meta:
		model = Perfil
		fields = ["telefono","email","cp","direccion","localidad","provincia","comunidad","pais"]


class RespuestaForm(forms.ModelForm):
	class Meta:
		model = Respuesta
		fields = ["alumno","pregunta","texto"]

class PhotoForm(forms.Form):
	photo = forms.ImageField()
