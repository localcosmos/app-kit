import os
from app_kit.utils import import_module

# appbuilder_version is an integer
def get_app_preview_builder_class(appbuilder_version):

    # the folder of a versoin start with a 'v', eg v1, v2 etc
    builder_path = 'app_kit.appbuilders.v%s.AppPreviewBuilder.AppPreviewBuilder' % appbuilder_version
    AppPreviewBuilderClass = import_module(builder_path)
    return AppPreviewBuilderClass


def get_app_release_builder_class(appbuilder_version):

    # the folder of a versoin start with a 'v', eg v1, v2 etc
    builder_path = 'app_kit.appbuilders.v%s.AppReleaseBuilder.AppReleaseBuilder' % appbuilder_version
    AppReleaseBuilderClass = import_module(builder_path)
    return AppReleaseBuilderClass


def get_available_appbuilder_versions(development=False):
    
    installed_appbuilders = []

    dirpath = os.path.join(os.path.dirname(os.path.abspath(__file__)))
    
    for name in os.listdir(dirpath):

        if name[0] != 'v':
            continue

        installed_appbuilders.append(name[1:])

    return installed_appbuilders


def get_latest_app_preview_builder(development=False):
    available = get_available_appbuilder_versions(development=development)

    available.sort()

    latest_version = available[-1]

    AppPreviewBuilderClass = get_app_preview_builder_class(latest_version)
    
    return AppPreviewBuilderClass()


def get_latest_app_release_builder(development=False):
    available = get_available_appbuilder_versions(development=development)

    available.sort()

    latest_version = available[-1]

    AppReleaseBuilderClass = get_app_release_builder_class(latest_version)
    
    return AppReleaseBuilderClass()
