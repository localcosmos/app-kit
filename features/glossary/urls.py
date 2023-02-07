from django.urls import path
from . import views

urlpatterns = [                    
    path('manage-glossary/<int:meta_app_id>/<int:content_type_id>/<int:object_id>/',
        views.ManageGlossary.as_view(), name='manage_glossary'),
    path('add-glossary-entry/<int:meta_app_id>/<int:glossary_id>/',
        views.AddGlossaryEntry.as_view(), name='add_glossary_entry'),
    path('edit-glossary-entry/<int:meta_app_id>/<int:glossary_id>/<int:glossary_entry_id>/',
        views.ManageGlossaryEntry.as_view(), name='edit_glossary_entry'),
    path('get-glossary-entries/<int:meta_app_id>/<int:glossary_id>/',
        views.GetGlossaryEntries.as_view(), name='get_glossary_entries'),
    path('get-glossary-entry/<int:meta_app_id>/<int:glossary_entry_id>/',
        views.GetGlossaryEntry.as_view(), name='get_glossary_entry'),
    path('delete-glossary-entry/<int:pk>/',
        views.DeleteGlossaryEntry.as_view(), name='delete_glossary_entry'),
]
