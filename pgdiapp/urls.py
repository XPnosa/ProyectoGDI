from django.conf.urls import url
from pgdiapp.views import *

from . import views

# URLs

urlpatterns = [
	url(r'^$', views.index, name='index'),
	url(r'^error$', views.error, name='error'),
	url(r'^pwmod$', views.pwmod, name='pwmod'),
	url(r'^regmod$', views.regmod, name='regmod'),
	url(r'^funmod$', views.funmod, name='funmod'),
	url(r'^register$', views.register, name='register'),
	url(r'^login$', views.login_view, name='login_view'),
	url(r'^logout$', views.logout_view, name='logout_view'),
	url(r'^logout_redirect$', views.logoutr, name='logoutr'),
	url(r'^alumnos$', views.alumnos, name='alumnos'),
	url(r'^perfil/(?P<grado>[A-Z]+)/(?P<usuario>[a-zA-Z0-9]+)$', views.perfil, name='perfil'),
	url(r'^cuestionario/(?P<user_name>[a-zA-Z0-9]+)$', views.cuestionario, name='cuestionario'),
]
