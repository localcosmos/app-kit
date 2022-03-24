import uuid

from django.db.backends.postgresql.base import *
from django.db.backends.postgresql.base import DatabaseWrapper as BaseDatabaseWrapper

class server_side_cursors(object):
    """
    With block helper that enables and disables server side cursors.
    """
    def __init__(self, qs_or_using_or_connection, itersize=None):
        from django.db import connections
        from django.db.models.query import QuerySet
        
        self.itersize = itersize
        if isinstance(qs_or_using_or_connection, QuerySet):
            self.connection = connections[qs_or_using_or_connection.db]
        elif isinstance(qs_or_using_or_connection, basestring):
            self.connection = connections[qs_or_using_or_connection]
        else:
            self.connection = qs_or_using_or_connection
    
    def __enter__(self):
        self.connection.server_side_cursors = True
        self.connection.server_side_cursor_itersize = self.itersize
    
    def __exit__(self, type, value, traceback):
        self.connection.server_side_cursors = False
        self.connection.server_side_cursor_itersize = None

class DatabaseWrapper(BaseDatabaseWrapper):
    """
    Psycopg2 database backend that allows the use of server side cursors.
    
    Usage:
    
    qs = Model.objects.all()
    with server_side_cursors(qs, itersize=x):
        for item in qs.iterator():
            item.value
    
    """
    def __init__(self, *args, **kwargs):
        self.server_side_cursors = False
        self.server_side_cursor_itersize = None
        super().__init__(*args, **kwargs)
    
    def _cursor(self):
        """
        Returns a unique server side cursor if they are enabled, 
        otherwise falls through to the default client side cursors.
        """
        if self.server_side_cursors:
            # intialise the connection if we haven't already
            # this will waste a client side cursor, but only on the first call
            if self.connection is None:
                super()._cursor()
            
            # give the cursor a unique name which will invoke server side cursors
            cursor = self.connection.cursor(name='cur%s' % str(uuid.uuid4()).replace('-', ''))
            cursor.tzinfo_factory = None
            
            if self.server_side_cursor_itersize is not None:
                cursor.itersize = self.server_side_cursor_itersize
            
            return CursorWrapper(cursor)
        
        return super()._cursor()
