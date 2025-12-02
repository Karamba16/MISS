from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
urlpatterns = [
    path('accounts/login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(http_method_names=['post']), name='logout'),
    path('accounts/register/', views.register, name='register'),
    
    # Основные пути
    path('', views.analyze_text_stanza, name='analyze'),
    path('analyze/natasha/', views.analyze_text_natasha, name='analyze_natasha'),
    path('analyze/stanza/', views.analyze_text_stanza, name='analyze_stanza'),
    path('analyze/spacy/', views.analyze_text_spacy, name='analyze_spacy'),
    path('history/', views.history, name='history'),
    path('history/<int:analysis_id>/', views.view_analysis, name='view_analysis'),
    path('download/text/', views.download_text, name='download_text'),
    path('download/visualization/', views.download_visualization, name='download_visualization')

    


]
