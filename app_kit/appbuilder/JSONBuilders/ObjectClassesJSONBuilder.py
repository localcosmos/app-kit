from app_kit.appbuilder.JSONBuilders.JSONBuilder import JSONBuilder


'''
    Builds JSON for one ObjectClasses
'''
class ObjectClassesJSONBuilder(JSONBuilder):

    def build(self):

        object_classes_json = self._build_common_json()

        return object_classes_json

    
