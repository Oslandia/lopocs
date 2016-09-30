uwsgi:
    uid: !USER!
    gid: !USER!
    virtualenv: !VENV!
    master: true
    socket: /tmp/lopocs.sock
    chmod-socket: 666
    protocol: uwsgi
#    socket: !IP!:5000
#    protocol: http
    module: lopocs.wsgi:app
    processes: 4
    enable-threads: true
    lazy-apps: true
    need-app: true
    catch: exceptions=true
    logto2: /tmp/lopocs.log
    log-maxsize: 10000000
    env: LOPOCS_SETTINGS=/tmp/dbbuilder/lopocs.yml.!DB!
