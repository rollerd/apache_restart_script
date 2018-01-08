#!/usr/bin/python

# This simple script runs an apache configtest to check whether or not there are any errors in the apache config files that would prevent apache from restarting.
# If there are no errors, then apache is restarted, otherwise the errors are printed out for the user to see and apache will not restart
# Warnings that do not prevent an apache restart are also printed out for the user
# If a configtest fails, an email will be sent to the user/group specified in the EMAIL_TO global variable


from subprocess import Popen, PIPE
import sys
from email.mime.text import MIMEText
import time
import os
import glob

# Global variable for setting who error emails are sent to
EMAIL_TO = 'systems_team@someaddress'


class Color:
    '''
    Simple class for coloring text in the terminal - usage: print color.text('message', 'color')
    '''
    def __init__(self):
        self.set_color = ''
        self.endc = '\033[0m'
        self.colors = {'purple' : '\033[95m', 'blue' : '\033[94m', 'green' : '\033[92m', 'yellow' : '\033[93m', 'red' : '\033[91m'}
  
    def text(self, text, color):
        self.set_color = self.colors[color]
        return self.set_color + text + self.endc

# Instantiate Color object
color = Color()


def restarts_pending():
    tmp_file = glob.glob('/tmp/apacherestarting')
    if tmp_file:
        print color.text('apache is in the middle of being restarted by another user/process. Please try again in just a second :)\n', 'yellow')
        return 1
    else:
        return 0


def apache_configtest():
    '''
    Capture return code and stderr messages from apache configtest without printing them to the terminal
    '''
    result = Popen(['apachectl', 'configtest'], stdout=PIPE, stderr=PIPE)
    output, err = result.communicate()
  
    return result.returncode, err


def restart_apache():
    '''
    Restart apache, hiding any warning/error messages that would normally be printed
    '''
    Popen(['touch', '/tmp/apacherestarting'])
    restart = Popen(['service', 'httpd', 'restart'], stderr=PIPE)
    restart.wait()
    tmp_file = glob.glob('/tmp/apacherestarting')
    if tmp_file:
        Popen(['rm', '/tmp/apacherestarting'])
  

def main():
    '''
    Main function. If return code is > 0, do not restart, but do display errors. Otherwise, restart and show any warning messages
    '''
    return_code, errdata = apache_configtest()
   
    errs = errdata.split('\n') # Split error messages into list
    
    if not return_code: # Though it will not produce a non-zero return code, apache can have warnings that do not prevent a restart
        if len(errs) > 2: # stderr always returns 'syntax OK' and an empty string, so we look for more messages than that
            print color.text('There were no errors found, but the following warnings were produced: \n', 'yellow')
            for err in errs:
                print color.text(err, 'yellow')
        
        if restarts_pending():
            return 2
        else:
            restart_apache()
            return 0
   
    else:
        send_email(errs)
        print color.text('Cannot restart apache! The following errors were found: \n', 'red')
        for err in errs:
            print color.text(err, 'red')
        return 1


def send_email(errs):
    '''
    Simple emailing function
    '''
    current_time = time.time()
    user = os.environ['SUDO_USER']
    domain_name = '@wharton.upenn.edu'
    email_from = user + domain_name
    host = os.environ['HOSTNAME']
    subject = '{0} - apache user config error!'.format(host)
    heading = 'Cannot restart apache due to user config error\n -------------------------------------------------------------\n\n'
    content = '{0} User: {1} attempted to restart apache, but was unable to due to a config error: \n {2}'.format(heading, user, [err + '\n' for err in errs])
  
    msg = MIMEText(content)
    msg['Reply-to'] = email_from
    msg['To'] = EMAIL_TO
    msg['Subject'] = subject
    p = Popen(["/usr/sbin/sendmail", "-t"], stdin=PIPE)
    p.communicate(msg.as_string())


if __name__=='__main__':
    '''
    We want to return a code indicating whether or not the apache restart failed. Useful for scripts that will call this script.
    '''
    rcode = main()
    if rcode:
        sys.exit(rcode)
    else:
        sys.exit(0)
