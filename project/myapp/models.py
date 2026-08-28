from django.db import models

# Create your models here.
# Tables
# -------

# 1. user_login - id, uname, passwd, u_type
# 2. category_settings - id, category_name
# 3. image_pool - id, category_id, pic_path
# 5. test_history - id, staff_id, pic_path, dt, tm, status

# 1. user_login - id, uname, passwd, u_type
class user_login(models.Model):
    uname = models.CharField(max_length=100)
    passwd = models.CharField(max_length=25)
    u_type = models.CharField(max_length=10)

    def __str__(self):
        return self.uname

# 2. category_settings - id, category_name
class category_settings(models.Model):
    #id
    category_name = models.CharField(max_length=100)

# 3. image_pool - id, category_id, pic_path, result, dt, tm, d_type
class image_pool(models.Model):
    #id
    category_id = models.IntegerField()
    pic_path = models.CharField(max_length=300)
    result = models.CharField(max_length=300)
    dt = models.CharField(max_length=40, blank=True, default='')
    tm = models.CharField(max_length=40, blank=True, default='')
    d_type = models.CharField(max_length=10, default='image')
    


# 5. test_history - id, patient_id, pic_path, dt, tm, status, d_type
class test_history(models.Model):
    id
    staff_id =  models.IntegerField()
    pic_path = models.CharField(max_length=200)
    dt = models.CharField(max_length=40)
    tm = models.CharField(max_length=40)
    status = models.CharField(max_length=20)
    d_type = models.CharField(max_length=10, default='image')





class user_details(models.Model):
    user_id = models.IntegerField()
    fname = models.CharField(max_length=100)
    lname = models.CharField(max_length=200)
    gender = models.CharField(max_length=25)
    age = models.IntegerField()
    addr = models.CharField(max_length=500)
    pin = models.IntegerField()
    contact = models.IntegerField()
    email = models.CharField(max_length=25)

    def __str__(self):
        return self.fname

