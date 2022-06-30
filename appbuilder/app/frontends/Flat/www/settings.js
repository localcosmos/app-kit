"use strict";

// these settings exist to guarantee backwards compatibility since the switch theme -> frontend
// these settings cover only those settings which are required before mango.init() is called

var DATABASE_NAME = 'LocalCosmosApp';

// replacement for old settings.js, will be filled during upstart
var settings = {
	"FRONTEND_NAME" : "Flat Frontend",
    "DATABASES" : {
        "default" : {
            "ENGINE" : "SQLite.sqliteplugin",
            "NAME" : DATABASE_NAME,
            "VERSION" : 1,
        },
        "Android" : {
            "ENGINE" : "SQLite.sqliteplugin",
            "NAME" : DATABASE_NAME,
            "VERSION" : 1,
        },
        "iOS" : {
            "ENGINE" : "SQLite.sqliteplugin",
            "NAME" : DATABASE_NAME,
            "VERSION" : 1,
        },
        "browser" : {
            "ENGINE": "RemoteDB.remote",
            "NAME": DATABASE_NAME,
            "VERSION": 1, 
        },
    },
    "MIDDLEWARE" : ["MangoUserMiddleware"],
    "REMOTEDB_MIDDLEWARE" : ["LocalCosmosRemoteDBMiddleware"],
    "AUTHENTICATION_BACKENDS" : ["LocalCosmosRemoteAuthentication"],
    "CONTEXT_PROCESSORS" : ["request", "auth", "device", "history"],
    "LOGIN_VIEW" : "LoginView",
    "OPTIONS" : {},
    "THEME" : "Flat"
};