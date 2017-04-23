from django.conf.urls import url
from pgdiapp.views import *

from . import views

# URLs

urlpatterns = [
	url(r'^$', views.index, name='index'),
	url(r'^error$', views.error, name='error'),
	url(r'^regreso$', views.regreso, name='regreso'),
	url(r'^regmod$', views.regmod, name='regmod'),
	url(r'^funmod$', views.funmod, name='funmod'),
	url(r'^registro$', views.registro, name='registro'),
	url(r'^login$', views.login_view, name='login_view'),
	url(r'^logout$', views.logout_view, name='logout_view'),
	url(r'^logout_redirect$', views.logoutr, name='logoutr'),
	url(r'^chpasswd$', views.chpasswd, name='chpasswd'),
	url(r'^chpasswd_redirect$', views.chpasswdr, name='chpasswdr'),
	url(r'^alumnos$', views.alumnos, name='alumnos'),
	url(r'^pendientes$', views.pendientes, name='pendientes'),
	url(r'^noencontrado$', views.noencontrado, name='noencontrado'),
	url(r'^formatonovalido$', views.formatonovalido, name='formatonovalido'),
	url(r'^descarte/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)$', views.descarte, name='descarte'),
	url(r'^confirmar_descarte/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)$', views.confirmar_descarte, name='confirmar_descarte'),
	url(r'^perfil/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)$', views.perfil, name='perfil'),
	url(r'^perfil/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)/editar$', views.editar, name='editar'),
	url(r'^perfil/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)/foto$', views.subir_foto, name='subir_foto'),
	url(r'^perfil/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)/respuestas$', views.respuestas, name='respuestas'),
	url(r'^alta/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)$', views.alta, name='alta'),
	url(r'^baja/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)$', views.baja, name='baja'),
	url(r'^confirmar_baja/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)$', views.confirmar_baja, name='confirmar_baja'),
	url(r'^cuestionario/(?P<user_name>[a-zA-Z0-9]+)$', views.cuestionario, name='cuestionario'),
]
