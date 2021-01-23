import pwd, subprocess

c.JupyterHub.authenticator_class = 'nativeauthenticator.NativeAuthenticator'

c.Authenticator.admin_users = {'admin'}
c.JupyterHub.port = 8002
c.LocalAuthenticator.create_system_users=True
c.Authenticator.delete_invalid_users = True
c.DummyAuthenticator.password = "password"

def pre_spawn_hook(spawner):

    username = spawner.user.name

    try:

        pwd.getpwnam(username)

    except KeyError:

        subprocess.check_call(['useradd', '-ms', '/bin/bash', username])

c.Spawner.pre_spawn_hook = pre_spawn_hook
