from django.contrib.contenttypes.models import ContentType

class GenericContentValidator:
    
    def __init__(self, generic_content, instance, messages=[]):
        self.generic_content = generic_content
        self.instance = instance
        self.messages = messages

    def add(self, message):
        self.messages.append(message)

    def dump(self):

        generic_content_content_type = ContentType.objects.get_for_model(self.generic_content)

        instance_content_type = ContentType.objects.get_for_model(self.instance)

        entry = {
            'generic_content_content_type_id' : generic_content_content_type.id,
            'generic_content_id' : self.generic_content.id,
            'generic_content_verbose' : str(self.generic_content),
            'instance_content_type_id' : instance_content_type.id,
            'instance_id' : self.instance.id,
            'instance_verbose' : str(self.instance),
            'messages' : [str(m) for m in self.messages],
        }

        return entry
    

class ValidationError(GenericContentValidator):
    pass


class ValidationWarning(GenericContentValidator):
    pass
