"""project URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from . import views
from django.urls import path

urlpatterns = [
    path('', views.index, name='index'),
    path('index', views.index, name='index'),
    path('about', views.about, name='about'),
    path('contact', views.contact, name='contact'),

    path('admin_login', views.admin_login, name='admin_login'),
    path('admin_changepassword', views.admin_changepassword, name='admin_changepassword'),
    path('admin_logout', views.admin_logout, name='admin_logout'),
    path('admin_home', views.admin_home, name='admin_home'),

    path('admin_category_settings_add', views.admin_category_settings_add, name='admin_category_settings_add'),
    path('admin_category_settings_view', views.admin_category_settings_view, name='admin_category_settings_view'),
    path('admin_category_settings_edit', views.admin_category_settings_edit, name='admin_category_settings_edit'),
    path('admin_category_settings_delete', views.admin_category_settings_delete, name='admin_category_settings_delete'),

    path('admin_pic_pool_add', views.admin_pic_pool_add, name='admin_pic_pool_add'),
    path('admin_pic_pool_video_add', views.admin_pic_pool_video_add,name='admin_pic_pool_video_add'),
    path('admin_pic_pool_view', views.admin_pic_pool_view, name='admin_pic_pool_view'),
    path('admin_pic_pool_delete', views.admin_pic_pool_delete, name='admin_pic_pool_delete'),

    path('admin_staff_user_add', views.admin_staff_user_add, name='admin_staff_user_add'),
    path('admin_staff_user_view', views.admin_staff_user_view, name='admin_staff_user_view'),
    path('admin_staff_user_delete', views.admin_staff_user_delete, name='admin_staff_user_delete'),

    path('admin_camera_page', views.admin_camera_page, name='admin_camera_page'),
    

    path('staff_login', views.staff_login, name='staff_login'),
    path('staff_logout', views.staff_logout, name='staff_logout'),
    path('staff_home', views.staff_home, name='staff_home'),
    path('staff_changepassword', views.staff_changepassword, name='staff_changepassword'),


    path('staff_test_history_add', views.staff_test_history_add, name='staff_test_history_add'),
    path('staff_test_history_view', views.staff_test_history_view, name='staff_test_history_view'),
    path('staff_test_history_video_add', views.staff_test_history_video_add,name='staff_test_history_video_add'),

    path('staff_camera_page', views.staff_camera_page, name='staff_camera_page'),
    path('staff_save_frame', views.staff_save_frame, name='staff_save_frame'),
    path('staff_live_page', views.staff_live_page, name='staff_live_page'),
    

    path("camera_page", views.camera_page, name="camera_page"),
    path("save-frame/", views.save_frame, name="save_frame"),


]
