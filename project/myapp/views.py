"""Ai-WildEye Views Module.

This module contains all view functions for the Ai-WildEye application.
Views handle HTTP requests and responses, delegating business logic to
service modules where appropriate.
"""

import os
import glob
import logging
import random
import shutil
import string
from datetime import datetime

from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.conf import settings

from .models import user_login, category_settings, image_pool, test_history
from .config import Config
from .services.ml_service import MLService
from .services.camera_service import CameraService
from .services.email_service import EmailService
from .services.video_service import VideoService
from .services.auth_service import AuthService

logger = logging.getLogger(__name__)

# Import BASE_DIR for compatibility
from project.settings import BASE_DIR

# Alert labels - kept for backward compatibility
ALERT_LABELS = Config.ALERT_LABELS


def _get_frame_display_path(pic_path, best_frame):
    """Copy the best video frame into the media dir so it can be displayed.

    Returns the static/relative URL to the copied frame, or None.
    """
    if not best_frame or not os.path.exists(best_frame):
        return None

    ext = os.path.splitext(best_frame)[1] or '.jpg'
    suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=7))
    frame_name = f"{os.path.splitext(os.path.basename(pic_path))[0]}_{suffix}{ext}"
    frame_dest = os.path.join(BASE_DIR, f'myapp/static/myapp/media/{frame_name}')
    shutil.copyfile(best_frame, frame_dest)
    return f'../static/myapp/media/{frame_name}'


# ===========================================
# Public Pages
# ===========================================

def index(request):
    """Render the public home page."""
    return render(request, './myapp/index.html')


def about(request):
    """Render the about page."""
    return render(request, './myapp/about.html')


def contact(request):
    """Render the contact page."""
    return render(request, './myapp/contact.html')

########################### ADMIN ##############################

def admin_login(request):
    """Handle admin login."""
    if request.method == 'POST':
        un = request.POST.get('un')
        pwd = request.POST.get('pwd')
        
        # Use AuthService for authentication
        user_data = AuthService.authenticate(un, pwd, AuthService.USER_TYPE_ADMIN)
        
        if user_data:
            AuthService.login(request, user_data)
            return render(request, './myapp/admin_home.html')
        else:
            msg = 'Invalid Uname or Password !!!'
            return render(request, './myapp/admin_login.html', {'msg': msg})
    else:
        return render(request, './myapp/admin_login.html', {'msg': ''})


def admin_home(request):
    """Render admin home page."""
    if not AuthService.is_logged_in(request):
        return admin_login(request)
    return render(request, './myapp/admin_home.html')


def admin_logout(request):
    """Handle admin logout."""
    AuthService.logout(request)
    return admin_login(request)


def admin_changepassword(request):
    """Handle admin password change."""
    if request.method == 'POST':
        opasswd = request.POST.get('opasswd')
        npasswd = request.POST.get('npasswd')
        uname = request.session.get(AuthService.SESSION_USER_NAME)
        
        result = AuthService.change_password(
            uname, opasswd, npasswd, AuthService.USER_TYPE_ADMIN
        )
        
        if result['success']:
            context = {'msg': 'Password Changed'}
        else:
            context = {'msg': result.get('error', 'Password Not Changed')}
        
        return render(request, './myapp/admin_changepassword.html', context)
    else:
        return render(request, './myapp/admin_changepassword.html', {'msg': ''})

# 2. category_settings - id, category_name


def admin_category_settings_add(request):
    """Add a new email address for alerts."""
    if request.method == 'POST':
        category_name = request.POST.get('category_name')
        cs_obj = category_settings(category_name=category_name)
        cs_obj.save()
        context = {'msg': 'Record Added'}
        return render(request, './myapp/admin_category_settings_add.html', context)
    else:
        return render(request, './myapp/admin_category_settings_add.html')


def admin_category_settings_edit(request):
    """Edit an existing email address."""
    if request.method == 'POST':
        s_id = request.POST.get('s_id')
        category_name = request.POST.get('category_name')
        tm = category_settings.objects.get(id=int(s_id))

        tm.category_name = category_name
        tm.save()
        msg = 'Record Updated'
        tm_l = category_settings.objects.all()
        context = {'category_list': tm_l, 'msg': msg}
        return render(request, './myapp/admin_category_settings_view.html', context)
    else:
        id = request.GET.get('id')
        tm = category_settings.objects.get(id=int(id))
        context = {'category_name': tm.category_name, 's_id': tm.id}
        return render(request, './myapp/admin_category_settings_edit.html', context)


def admin_category_settings_delete(request):
    """Delete an email address."""
    id = request.GET.get('id')
    logger.info(f"Deleting category with id: {id}")
    tm = category_settings.objects.get(id=int(id))
    tm.delete()
    msg = 'Record Deleted'
    tm_l = category_settings.objects.all()
    context = {'category_list': tm_l, 'msg': msg}
    return render(request, './myapp/admin_category_settings_view.html', context)


def admin_category_settings_view(request):
    """View all email addresses."""
    tm_l = category_settings.objects.all()
    context = {'category_list': tm_l}
    return render(request, './myapp/admin_category_settings_view.html', context)

# 3. image_pool - id, category_id, pic_path

from django.core.files.storage import FileSystemStorage


def admin_pic_pool_video_add(request):
    """Admin video upload and analysis."""
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        pic_path = fs.save(uploaded_file.name, uploaded_file)
        
        # Video extraction
        video_file_path = os.path.join(BASE_DIR, f'myapp/static/myapp/media/{pic_path}')
        video_result = VideoService.convert(video_file_path)
        
        # Handle extraction failure before running ML prediction
        if not video_result.get('success') or video_result.get('frame_count', 0) == 0:
            msg = f"Video processing failed: {video_result.get('error', 'no frames extracted')}"
            context = {
                'title': 'Video File Analysis',
                'msg': msg
            }
            return render(request, 'myapp/admin_pic_pool_video_add.html', context)
        
        # ML prediction
        extracted_path = os.path.join(BASE_DIR, 'data/extracted')
        result_d = MLService.predict_from_dir(input_dir=extracted_path)
        
        # Copy best frame to media dir for display
        frame_path = _get_frame_display_path(pic_path, result_d.get('best_frame'))
        
        # Save to database
        category_id = 1
        dt = datetime.today().strftime('%Y-%m-%d')
        tm = datetime.today().strftime('%H:%M:%S')
        pic_obj = image_pool(pic_path=pic_path, result=result_d['animal'], category_id=category_id,
                             dt=dt, tm=tm, d_type='video')
        pic_obj.save()
        
        context = {
            'title': 'Video File Analysis',
            'pic_path': pic_path,
            'frame_path': frame_path,
            'msg': f"Predicted Animal: {result_d['animal']} ({result_d['match']} confidence)"
        }
        return render(request, 'myapp/admin_pic_pool_video_add.html', context)
    else:
        context = {'title': 'Video File Analysis'}
        return render(request, 'myapp/admin_pic_pool_video_add.html', context)


def admin_pic_pool_add(request):
    """Admin image upload and analysis."""
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        pic_path = fs.save(uploaded_file.name, uploaded_file)
        
        # ML prediction
        input_image = os.path.join(BASE_DIR, f'myapp/static/myapp/media/{pic_path}')
        result_d = MLService.predict_from_file(input_image=input_image)
        
        # Save to database
        category_id = 1
        dt = datetime.today().strftime('%Y-%m-%d')
        tm = datetime.today().strftime('%H:%M:%S')
        pic_obj = image_pool(pic_path=pic_path, result=result_d['animal'], category_id=category_id,
                             dt=dt, tm=tm, d_type='image')
        pic_obj.save()
        
        context = {
            'title': 'Image File Analysis',
            'pic_path': pic_path,
            'msg': f"Predicted Animal: {result_d['animal']} ({result_d['match']} confidence)"
        }
        return render(request, 'myapp/admin_pic_pool_add.html', context)
    else:
        context = {'title': 'Image File Analysis'}
        return render(request, 'myapp/admin_pic_pool_add.html', context)


def admin_pic_pool_delete(request):
    """Delete an image pool record."""
    id = request.GET.get('id')
    logger.info(f"Deleting image pool record with id: {id}")
    
    lm = image_pool.objects.get(id=int(id))
    lm.delete()
    
    pp_l = image_pool.objects.all()
    
    # Preserve current filter after deletion
    d_type = request.GET.get('type', '')
    if d_type in ('image', 'video', 'live'):
        pp_l = pp_l.filter(d_type=d_type)
    
    pp_l = pp_l.order_by('-id')[:20]
    cm_l = category_settings.objects.all()
    
    context = {'pic_list': pp_l, 'category_list': cm_l, 'current_filter': d_type}
    return render(request, 'myapp/admin_pic_pool_view.html', context)


def admin_pic_pool_view(request):
    """View latest 20 image pool records, newest first."""
    pp_l = image_pool.objects.all()
    
    # Filter by detection type (image, video, live)
    d_type = request.GET.get('type', '')
    if d_type in ('image', 'video', 'live'):
        pp_l = pp_l.filter(d_type=d_type)
    
    pp_l = pp_l.order_by('-id')[:20]
    cm_l = category_settings.objects.all()
    cmd = {}
    for nm in cm_l:
        cmd[nm.id] = nm.category_name
    
    context = {'pic_list': pp_l, 'category_list': cmd, 'current_filter': d_type}
    return render(request, 'myapp/admin_pic_pool_view.html', context)

def admin_staff_user_add(request):
    """Add a new staff user."""
    if request.method == 'POST':
        uname = request.POST.get('uname')
        password = request.POST.get('password')
        u_type = 'staff'

        ul = user_login(uname=uname, passwd=password, u_type=u_type)
        ul.save()
        context = {'msg': 'Staff Created'}
        return render(request, 'myapp/admin_staff_user_add.html', context)
    else:
        return render(request, 'myapp/admin_staff_user_add.html')


def admin_staff_user_delete(request):
    """Delete a staff user."""
    id = request.GET.get('id')
    logger.info(f"Deleting staff user with id: {id}")
    
    nm = user_login.objects.get(id=int(id))
    nm.delete()
    
    nm_l = user_login.objects.filter(u_type='staff')
    context = {'staff_list': nm_l}
    return render(request, 'myapp/admin_staff_user_view.html', context)


def admin_staff_user_view(request):
    """View all staff users."""
    nm_l = user_login.objects.filter(u_type='staff')
    context = {'staff_list': nm_l}
    return render(request, 'myapp/admin_staff_user_view.html', context)

# Camera views using CameraService and MLService

# Session key used to remember the IP camera address the user selects.
SESSION_CAMERA_IP = "camera_ip"


def _get_session_camera_ip(request):
    """Return the camera IP stored in the user's session, or None."""
    return request.session.get(SESSION_CAMERA_IP)


@require_POST
def set_camera_ip(request):
    """Verify and store the user-provided IP camera address in the session.

    The camera is tested for connectivity first. Only if it is reachable is
    the IP saved and a success message returned.
    """
    ip = request.POST.get("ip", "").strip()
    if not ip:
        return JsonResponse(
            {"success": False, "message": "Please enter an IP address."},
            status=400,
        )

    connection = CameraService.test_connection(ip)
    if not connection['success']:
        return JsonResponse(
            {"success": False, "message": connection.get('error', 'Could not connect to camera.')},
            status=400,
        )

    request.session[SESSION_CAMERA_IP] = ip
    return JsonResponse({"success": True, "video_url": connection['video_url']})


@require_POST
def disconnect_camera(request):
    """Disconnect the currently connected IP camera.

    Clears the camera IP from the session so the app no longer captures
    from the previously selected camera.
    """
    request.session.pop(SESSION_CAMERA_IP, None)
    return JsonResponse({"success": True, "message": "Camera disconnected."})


def admin_camera_page(request):
    """Show live video and a button to capture a snapshot (Admin)."""
    ip = _get_session_camera_ip(request)
    video_url = CameraService.get_video_url(ip)
    return render(request, "myapp/admin_camera_page.html", {"video_url": video_url, "camera_ip": ip})


def admin_live_page(request):
    """Show live camera feed with auto-capture (Admin)."""
    ip = _get_session_camera_ip(request)
    video_url = CameraService.get_video_url(ip)
    return render(request, "myapp/admin_live_page.html", {"video_url": video_url, "camera_ip": ip})


@require_POST
def admin_save_frame(request):
    """Capture frame, analyze, and send alerts if wild animal detected (Admin)."""
    # Capture and save frame
    ip = _get_session_camera_ip(request)
    result = CameraService.capture_and_save(ip)

    if not result['success']:
        return JsonResponse({"success": False, "message": result['error']}, status=500)

    # Run ML prediction
    result_d = MLService.predict_from_file(input_image=result['filepath'])

    message = f"Predicted Animal: {result_d['animal']} ({result_d['match']} confidence)"

    # Check for wild animal and trigger alerts
    if result_d['animal'] in ALERT_LABELS:
        # Play alert sound
        try:
            from playsound import playsound
            audio_path = os.path.join(BASE_DIR, 'backend/audio/alert.mp3')
            if os.path.exists(audio_path):
                playsound(audio_path)
        except Exception as e:
            logger.warning(f"Failed to play alert sound: {e}")

        # Send email alerts
        email_list = category_settings.objects.all()
        for email in email_list:
            EmailService.send_mail("Alert", message, email.category_name)

    # Save live detection to admin's history (image_pool)
    dt = datetime.today().strftime('%Y-%m-%d')
    tm = datetime.today().strftime('%H:%M:%S')
    pic_obj = image_pool(
        pic_path=f'captures/{result["filename"]}',
        result=result_d['animal'], category_id=1,
        dt=dt, tm=tm, d_type='live'
    )
    pic_obj.save()

    return JsonResponse({
        "success": True,
        "message": message,
        "filename": result['filename'],
        "file_url": result['file_url'],
    })


def camera_page(request):
    """Show live video and a button to capture a snapshot."""
    ip = _get_session_camera_ip(request)
    video_url = CameraService.get_video_url(ip)
    return render(request, "myapp/camera_page.html", {"video_url": video_url, "camera_ip": ip})


@require_POST
def save_frame(request):
    """Capture a frame from IP camera, analyze it, and return results."""
    # Capture and save frame
    ip = _get_session_camera_ip(request)
    result = CameraService.capture_and_save(ip)
    
    if not result['success']:
        return JsonResponse({"success": False, "message": result['error']}, status=500)
    
    # Run ML prediction
    result_d = MLService.predict_from_file(input_image=result['filepath'])
    
    message = f"Predicted Animal: {result_d['animal']} ({result_d['match']} confidence)"
    
    return JsonResponse({
        "success": True,
        "message": message,
        "filename": result['filename'],
        "file_url": result['file_url'],
    })


#################
##############################################################################
################################## STAFF ########################
######STAFF###########

def staff_login(request):
    """Handle staff login."""
    if request.method == 'POST':
        uname = request.POST.get('uname')
        passwd = request.POST.get('passwd')
        
        # Use AuthService for authentication
        user_data = AuthService.authenticate(uname, passwd, AuthService.USER_TYPE_STAFF)
        
        if user_data:
            AuthService.login(request, user_data)
            context = {'uname': user_data['uname']}
            return render(request, 'myapp/staff_home.html', context)
        else:
            context = {'msg': 'Invalid Credentials !!!'}
            return render(request, 'myapp/staff_login.html', context)
    else:
        return render(request, 'myapp/staff_login.html')


def staff_home(request):
    """Render staff home page."""
    if not AuthService.is_logged_in(request):
        return staff_login(request)
    
    context = {'uname': request.session.get(AuthService.SESSION_USER_NAME)}
    return render(request, './myapp/staff_home.html', context)


def staff_changepassword(request):
    """Handle staff password change."""
    if request.method == 'POST':
        uname = request.session.get(AuthService.SESSION_USER_NAME)
        new_password = request.POST.get('new_password')
        current_password = request.POST.get('current_password')
        
        result = AuthService.change_password(
            uname, current_password, new_password, AuthService.USER_TYPE_STAFF
        )
        
        if result['success']:
            return render(request, './myapp/staff_settings.html')
        else:
            return render(request, './myapp/staff_changepassword.html')
    else:
        return render(request, './myapp/staff_changepassword.html')


def staff_logout(request):
    """Handle staff logout."""
    AuthService.logout(request)
    return staff_login(request)


from .models import test_history
from datetime import datetime
from django.core.files.storage import FileSystemStorage


def staff_test_history_add(request):
    """Staff image upload and analysis."""
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        pic_path = fs.save(uploaded_file.name, uploaded_file)
        
        # ML prediction
        input_image = os.path.join(BASE_DIR, f'myapp/static/myapp/media/{pic_path}')
        result_d = MLService.predict_from_file(input_image=input_image)
        
        # Save to database
        staff_id = int(request.session.get(AuthService.SESSION_USER_ID))
        dt = datetime.today().strftime('%Y-%m-%d')
        tm = datetime.today().strftime('%H:%M:%S')
        status = result_d['animal']
        
        th_obj = test_history(pic_path=pic_path, staff_id=staff_id, dt=dt, tm=tm, status=status, d_type='image')
        th_obj.save()
        
        # Determine animal type
        animal_type = 'Domestic'
        if result_d['animal'] in ALERT_LABELS:
            animal_type = 'Wild'
        
        context = {
            'pic_path': pic_path,
            'msg': f"Predicted Animal: {result_d['animal']}({animal_type}) ({result_d['match']} confidence)"
        }
        return render(request, 'myapp/staff_test_history_add.html', context)
    else:
        staff_id = int(request.session.get(AuthService.SESSION_USER_ID))
        context = {'staff_id': staff_id}
        return render(request, 'myapp/staff_test_history_add.html', context)


def staff_test_history_video_add(request):
    """Staff video upload and analysis."""
    if request.method == 'POST':
        uploaded_file = request.FILES['document']
        fs = FileSystemStorage()
        pic_path = fs.save(uploaded_file.name, uploaded_file)
        
        # Video extraction
        video_file_path = os.path.join(BASE_DIR, f'myapp/static/myapp/media/{pic_path}')
        video_result = VideoService.convert(video_file_path)
        
        # Handle extraction failure before running ML prediction
        if not video_result.get('success') or video_result.get('frame_count', 0) == 0:
            msg = f"Video processing failed: {video_result.get('error', 'no frames extracted')}"
            context = {'msg': msg}
            return render(request, 'myapp/staff_test_history_video_add.html', context)
        
        # ML prediction
        extracted_path = os.path.join(BASE_DIR, 'data/extracted')
        result_d = MLService.predict_from_dir(input_dir=extracted_path)
        
        # Copy best frame to media dir for display
        frame_path = _get_frame_display_path(pic_path, result_d.get('best_frame'))
        
        # Save to database
        staff_id = int(request.session.get(AuthService.SESSION_USER_ID))
        dt = datetime.today().strftime('%Y-%m-%d')
        tm = datetime.today().strftime('%H:%M:%S')
        status = result_d['animal']
        
        th_obj = test_history(pic_path=pic_path, staff_id=staff_id, dt=dt, tm=tm, status=status, d_type='video')
        th_obj.save()
        
        # Determine animal type
        animal_type = 'Domestic'
        if result_d['animal'] in ALERT_LABELS:
            animal_type = 'Wild'
        
        context = {
            'pic_path': pic_path,
            'frame_path': frame_path,
            'msg': f"Predicted Animal: {result_d['animal']}({animal_type}) ({result_d['match']} confidence)"
        }
        return render(request, 'myapp/staff_test_history_video_add.html', context)
    else:
        staff_id = int(request.session.get(AuthService.SESSION_USER_ID))
        context = {'staff_id': staff_id}
        return render(request, 'myapp/staff_test_history_video_add.html', context)


def staff_test_history_view(request):
    """View staff test history."""
    staff_id = int(request.session.get(AuthService.SESSION_USER_ID))
    test_l = test_history.objects.filter(staff_id=staff_id)
    
    # Filter by detection type (image, video, live)
    d_type = request.GET.get('type', '')
    if d_type in ('image', 'video', 'live'):
        test_l = test_l.filter(d_type=d_type)
    
    test_l = test_l.order_by('-id')[:20]
    
    context = {'test_list': test_l, 'current_filter': d_type}
    return render(request, 'myapp/staff_test_history_view.html', context)


def staff_test_history_delete(request):
    """Delete a staff test history record."""
    id = request.GET.get('id')
    logger.info(f"Deleting staff test history record with id: {id}")

    staff_id = int(request.session.get(AuthService.SESSION_USER_ID))
    th = test_history.objects.filter(id=int(id), staff_id=staff_id).first()
    if th:
        th.delete()

    test_l = test_history.objects.filter(staff_id=staff_id)

    d_type = request.GET.get('type', '')
    if d_type in ('image', 'video', 'live'):
        test_l = test_l.filter(d_type=d_type)

    test_l = test_l.order_by('-id')[:20]

    context = {'test_list': test_l, 'current_filter': d_type}
    return render(request, 'myapp/staff_test_history_view.html', context)




def staff_camera_page(request):
    """Show live video and a button to capture a snapshot (Staff)."""
    ip = _get_session_camera_ip(request)
    video_url = CameraService.get_video_url(ip)
    return render(request, "myapp/staff_camera_page.html", {"video_url": video_url, "camera_ip": ip})


def staff_live_page(request):
    """Show live camera feed with auto-capture (Staff)."""
    ip = _get_session_camera_ip(request)
    video_url = CameraService.get_video_url(ip)
    return render(request, "myapp/staff_live_page.html", {"video_url": video_url, "camera_ip": ip})


@require_POST
def staff_save_frame(request):
    """Capture frame, analyze, and send alerts if wild animal detected."""
    # Capture and save frame
    ip = _get_session_camera_ip(request)
    result = CameraService.capture_and_save(ip)
    
    if not result['success']:
        return JsonResponse({"success": False, "message": result['error']}, status=500)
    
    # Run ML prediction
    result_d = MLService.predict_from_file(input_image=result['filepath'])
    
    message = f"Predicted Animal: {result_d['animal']} ({result_d['match']} confidence)"
    
    # Check for wild animal and trigger alerts
    if result_d['animal'] in ALERT_LABELS:
        # Play alert sound
        try:
            from playsound import playsound
            audio_path = os.path.join(BASE_DIR, 'backend/audio/alert.mp3')
            if os.path.exists(audio_path):
                playsound(audio_path)
        except Exception as e:
            logger.warning(f"Failed to play alert sound: {e}")
        
        # Send email alerts
        email_list = category_settings.objects.all()
        for email in email_list:
            EmailService.send_mail("Alert", message, email.category_name)
    
    # Save live detection to history
    staff_id = int(request.session.get(AuthService.SESSION_USER_ID))
    dt = datetime.today().strftime('%Y-%m-%d')
    tm = datetime.today().strftime('%H:%M:%S')
    th_obj = test_history(
        pic_path=f'captures/{result["filename"]}',
        staff_id=staff_id, dt=dt, tm=tm,
        status=result_d['animal'], d_type='live'
    )
    th_obj.save()
    
    # Also save to image_pool so the live capture appears in the admin's
    # Test History (admin page reads from image_pool, staff from test_history).
    pic_obj = image_pool(
        pic_path=f'captures/{result["filename"]}',
        result=result_d['animal'], category_id=1,
        dt=dt, tm=tm, d_type='live'
    )
    pic_obj.save()
    
    return JsonResponse({
        "success": True,
        "message": message,
        "filename": result['filename'],
        "file_url": result['file_url'],
    })

#############################################################



# def user_details_add(request):
#     if request.method == 'POST':

#         fname = request.POST.get('fname')
#         lname = request.POST.get('lname')

#         gender = request.POST.get('gender')
#         age = request.POST.get('age')
#         addr = request.POST.get('addr')
#         pin = request.POST.get('pin')
#         email = request.POST.get('email')
#         contact = request.POST.get('contact')
#         password = request.POST.get('pwd')
#         uname=email
#         #status = "new"

#         ul = user_login(uname=uname, passwd=password, u_type='user')
#         ul.save()
#         user_id = user_login.objects.all().aggregate(Max('id'))['id__max']

#         ud = user_details(user_id=user_id,fname=fname, lname=lname, gender=gender, age=age,addr=addr, pin=pin, contact=contact, email=email )
#         ud.save()

#         print(user_id)
#         context = {'msg': 'User Registered'}
#         return render(request, 'myapp/user_login.html',context)

#     else:
#         return render(request, 'myapp/user_details_add.html')


