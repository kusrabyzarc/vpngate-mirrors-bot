import os
def update():
    filenames = ['mirrors.csv', 'mirrors.json', 'README.md']

    # Copying...
    for filename in filenames:
        with open(os.path.join('public', filename)) as file_in:
            with open(os.path.join('..', 'vpngate-daily-mirrors', filename), 'w') as file_out:
                file_out.write(file_in.read())

    # Pushing...
    os.chdir(os.path.join('..', 'vpngate-daily-mirrors'))
    os.system('git add -A')
    os.system('git commit -m "Update"')
    os.system('git push ')
    # os.system(os.path.join('..', 'vpngate-mirrors-bot', 'script_pusher.bat')
    os.chdir(os.path.join('..', 'vpngate-mirrors-bot'))
