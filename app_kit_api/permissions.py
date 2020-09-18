from rest_framework import permissions


class IsApiUser(permissions.BasePermission):
    
    def has_permission(self, request, view):
        
        if request.user.username != 'APPKITAPIUSER':
            return False

        return True
        


