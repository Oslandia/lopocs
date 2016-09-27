uwsgi:
    plugin: python3.4
    virtualenv: /home/blottiere/.virtualenvs/lightpcss/
    master: true
    socket: !IP!:5000
    module: lopocs.wsgi:app
    processes: 4
    enable-threads: true
    lazy-apps: true
    protocol: http
    need-app: true
    catch: exceptions=true
    env: LOPOCS_SETTINGS=/tmp/dbbuilder/lightpcss.yml.!DB!
