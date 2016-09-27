flask:
    DEBUG: True
    LOG_LEVEL: debug
    PG_HOST: !HOST!
    PG_NAME: !DB!
    PG_PORT: 5432
    PG_USER: !USER!
    PG_PASSWORD:
    PG_COLUMN: !TABLE!
    PG_TABLE: !TABLE!
    DEPTH: 6
    METHOD: midoc
    BB: [!XMIN!, !YMIN!, !ZMIN!, !XMAX!, !YMAX!, !ZMAX!]
    LIMIT: 10000
