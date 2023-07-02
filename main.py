import imaplib
import email
import json
import time
from datetime import datetime
nowtime = datetime.now
import git_updater
import os

blank_cfg = '''{
    "username": "your@mail.ru",
    "mail_pass": "your_password",
    "imap_server": "imap.mail.ru",
    "folder": "INBOX"
}'''

txt_level = ['INFO', 'WARNING', 'ERROR']
class LOGLEVEL:
    INFO = 0
    WARNING = 1
    ERROR = 2
    
def log(message, level=0):
    msg = f'[{str(nowtime()).split(".")[0]}] [{txt_level[level]}] {message}'
    with open('log.txt', 'a') as log_file:
        log_file.write(msg + '\n')
    if level < 2:
        print(msg)
    

def control(answer, mail=False):
    ''' Controller and parser for answers '''
    
    if answer[0] == 'OK':
        # Return decoded answer
        if mail:
            data = email.message_from_bytes(answer[1][0][1])
            return data
        else:
            data = list( map ( lambda answ: answ.decode() , answer[1] ) )
            if len(data) == 1: return data[0]

        # I don't know if this is possible, so I want to keep it
        raise OverflowError(f'Recieved scary long data\n{answer}\nStopping...')

    # Throwing error if server answered sth like 'NO' or 'BAD'
    raise ValueError(f'Server just anwered:\n{answer}\nStopping...')

# Authorization attempt
try:
    with open('config.cfg', 'r') as cfg:
        settings = json.loads(cfg.read())
    mail_pass = settings['mail_pass']
    username = settings['username']
    imap_server = settings['imap_server']
    folder = settings['folder']
except FileNotFoundError:
    with open('config.cfg', 'w') as cfg:
        cfg.write(blank_cfg)
    log('Authorization data is not spicified yet. Please, do it in config.cfg', LOGLEVEL.WARNING)
    exit(1)

def check_inbox():
    global imap
    imap = imaplib.IMAP4_SSL(imap_server)

    # Authorization
    try:
        log('Authorization attempt...')
        control(imap.login(username, mail_pass))
    except Exception as e:
        log(f'Authorization error. {e}', LOGLEVEL.ERROR)
        raise e
    log('Authorized.')
    
    # Folder select
    try:
        log(f'Changing folder to {folder}...')
        control(imap.select(folder))
    except Exception as e:
        log('Folder changing error. Seens like it does not exist...', LOGLEVEL.ERROR)
        raise e
    
    # Get messages
    message_ids = control(imap.search(None, 'ALL'))
    message_ids = message_ids.split(' ')[::-1]
    
    for message_id in message_ids:
        
        # Raw mail data getting
        raw_mail = control(imap.fetch(message_id, '(RFC822)'), mail=True)
    
        # Caught latest message by VPNGate
        if raw_mail['from'] == '"VPN Gate Daily Mirrors" <vpngate-daily@vpngate.net>':
            
            log('Found message...')
            # Parsing raw data into payload
            
            payload = str(raw_mail).split('\n')
            payload = payload[ payload.index(f'Hi {username},') : ]

            # TODO: Save full e-mail too.
            full_message = payload[:]
            
            payload = payload[4:]
            
            # Pushing to list
            mirrors = []
            i = 0
            while payload[i] != '' and int(payload[i][0]) == i//3 + 1:
                mirrors.append({})
                ip_port = payload[i][10:-1].split(':')
                mirrors[-1]['IP'] = ip_port[0]
                mirrors[-1]['PORT'] = int(ip_port[1])
                mirrors[-1]['LOCATION'] = payload[i + 1].split(': ')[-1][:-1]
                i += 3
                

            new_mirrors = json.dumps(mirrors)
            
            # Check if mirrors are updated
            try:
                with open(os.path.join('public', 'mirrors.json'), 'r') as mirrors_file:
                    old_mirrors = mirrors_file.read()
            except FileNotFoundError:
                old_mirrors = None
            log('Compairing...')
            if old_mirrors != new_mirrors:
                log('There is new mirrors. Updating...', LOGLEVEL.WARNING)
                
                # Update json with mirrors
                with open(os.path.join('public', 'mirrors.json'), 'w') as mirrors_file:
                    mirrors_file.write(new_mirrors)

                # Update csv with mirrors
                with open(os.path.join('public', 'mirrors.csv'), 'w') as mirrors_file:
                    data = ['IP,PORT,LOCATION']
                    for mirror in mirrors:
                        data.append(','.join(map(str, mirror.values())))
                    mirrors_file.write('\n'.join(data))
                                
                # Update README.md
                with open(os.path.join('public', 'README.md'), 'w') as readme:
                    full_message[0] = 'Hello, %username%,'
                    full_message.insert(0, '# vpngate-daily-mirrors\n')
                    readme.write('\n'.join(full_message))

                log('Updated.')
                return True
            return False

while True:
    log('Checking...')
    if check_inbox():
        log('Mirrors updated! Starting Git pushing...', LOGLEVEL.WARNING)
        git_updater.update()
        log('Pushed.')
    else: log('There is no update.')

    # Closing connection
    log('Closing collection...')
    imap.close()
    imap.logout()
    del imap
    log('Connection closed')
    
    time.sleep(60 * 60) # Every 1 hour
