from app_kit.appbuilders.AppBuilderBase import AppBuilderBase

class AppBuilder(AppBuilderBase):

    @property
    def version(self):
        return 1

    # development or released
    @property
    def status(self):
        return 'development'


    def _get_empty_settings(self, meta_app, app_version=None):

        if app_version == None:
            app_version = meta_app.current_version
        
        settings = {
            "NAME" : meta_app.name,
            "PACKAGE_NAME" : meta_app.package_name,
            "DATABASES" : {
                "default" : {
                    "ENGINE" : "SQLite.sqliteplugin",
		    "NAME" : meta_app.package_name,
		    "VERSION" : 1,
                },
                "Android" : {
		    "ENGINE" : "SQLite.sqliteplugin",
		    "NAME" : meta_app.package_name,
		    "VERSION" : 1,
		},
                "iOS" : {
		    "ENGINE" : "SQLite.sqliteplugin",
		    "NAME" : meta_app.package_name,
		    "VERSION" : 1,
		},
                "browser" : {
                    "ENGINE": "RemoteDB.remote",
                    "NAME": meta_app.package_name,
                    "VERSION": 1, 
                },
            },
            "LANGUAGES" : [language_code for language_code in meta_app.languages()], # the languages supported by this app
            "PRIMARY_LANGUAGE" : meta_app.primary_language, # primary language is the fallback language
            "THEME" : None,
            "APP_UID" : meta_app.app.uid,
            "APP_UUID" : str(meta_app.uuid),
            "APP_VERSION" : app_version,
            "OPTIONS" : {},
            "API_URL" : None,
            "MIDDLEWARE" : ["MangoUserMiddleware"],
            "REMOTEDB_API_URL" : None,
            "REMOTEDB_MIDDLEWARE" : ["LocalCosmosRemoteDBMiddleware"],
            "AUTHENTICATION_BACKENDS" : ["LocalCosmosRemoteAuthentication"],
            "CONTEXT_PROCESSORS" : ["request", "auth", "device", "history"],
            "LOGIN_VIEW" : "LoginView",
            "PREVIEW" : False, # True is only needed for previewing online_content, preview hides login/register
        }
        
        return settings
