# Click on the following link and create app password then provide that
# https://myaccount.google.com/lesssecureapps
# https://myaccount.google.com/apppasswords


# your Gmail account
import smtplib

def send_mail(subject,message,to):

    # creates SMTP session
    s = smtplib.SMTP('smtp.gmail.com', 587)

    # start TLS for security
    s.starttls()

    # Authentication
    gmail_id = 'wildeye2026@gmail.com'
    gmail_password = "rgww pfxi huno frig"
    s.login(gmail_id, gmail_password)

    # message to be sent
    message = 'Subject: {}\n\n{}'.format(subject, message)

    # sending the mail
    s.sendmail(gmail_id, to, message)

    print(to, message)

    # terminating the session
    s.quit()

#send_mail("heoo","hai",'nx.sarath@gmail.com')