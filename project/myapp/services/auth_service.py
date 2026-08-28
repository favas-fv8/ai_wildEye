"""Authentication Service for user management.

This service handles all authentication-related operations including:
- User login/logout
- Session management
- Password changes
- User type validation
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class AuthService:
    """Service for authentication operations."""
    
    # User types
    USER_TYPE_ADMIN = 'admin'
    USER_TYPE_STAFF = 'staff'
    USER_TYPE_USER = 'user'
    
    # Session keys
    SESSION_USER_NAME = 'user_name'
    SESSION_USER_ID = 'user_id'
    
    @classmethod
    def authenticate(
        cls,
        username: str,
        password: str,
        user_type: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a user with username and password.
        
        Args:
            username: Username to authenticate
            password: Password to verify
            user_type: Optional user type filter ('admin', 'staff', 'user')
            
        Returns:
            User dictionary if authentication successful, None otherwise
        """
        from myapp.models import user_login
        
        try:
            # Build filter
            filter_kwargs = {
                'uname': username,
                'passwd': password
            }
            
            if user_type:
                filter_kwargs['u_type'] = user_type
            
            # Query database
            users = user_login.objects.filter(**filter_kwargs)
            
            if users.exists():
                user = users.first()
                logger.info(f"User authenticated: {username} (type: {user.u_type})")
                return {
                    'id': user.id,
                    'uname': user.uname,
                    'u_type': user.u_type
                }
            
            logger.warning(f"Authentication failed for: {username}")
            return None
            
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return None
    
    @classmethod
    def login(cls, request, user_data: Dict[str, Any]) -> None:
        """Set user session data after successful authentication.
        
        Args:
            request: Django request object
            user_data: User data dictionary from authenticate()
        """
        request.session[cls.SESSION_USER_NAME] = user_data['uname']
        request.session[cls.SESSION_USER_ID] = user_data['id']
        logger.info(f"User logged in: {user_data['uname']}")
    
    @classmethod
    def logout(cls, request) -> None:
        """Clear user session data.
        
        Args:
            request: Django request object
        """
        try:
            username = request.session.get(cls.SESSION_USER_NAME, 'Unknown')
            del request.session[cls.SESSION_USER_NAME]
            del request.session[cls.SESSION_USER_ID]
            logger.info(f"User logged out: {username}")
        except KeyError:
            logger.warning("Session data not found during logout")
    
    @classmethod
    def is_logged_in(cls, request) -> bool:
        """Check if a user is currently logged in.
        
        Args:
            request: Django request object
            
        Returns:
            True if user is logged in, False otherwise
        """
        return cls.SESSION_USER_ID in request.session
    
    @classmethod
    def get_current_user(cls, request) -> Optional[Dict[str, Any]]:
        """Get current logged-in user data from session.
        
        Args:
            request: Django request object
            
        Returns:
            User dictionary if logged in, None otherwise
        """
        if not cls.is_logged_in(request):
            return None
        
        return {
            'id': request.session.get(cls.SESSION_USER_ID),
            'uname': request.session.get(cls.SESSION_USER_NAME)
        }
    
    @classmethod
    def change_password(
        cls,
        username: str,
        current_password: str,
        new_password: str,
        user_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """Change a user's password.
        
        Args:
            username: Username of the user
            current_password: Current password for verification
            new_password: New password to set
            user_type: Optional user type filter
            
        Returns:
            Dictionary with 'success' and optional 'error' keys
        """
        from myapp.models import user_login
        
        try:
            # Build filter
            filter_kwargs = {
                'uname': username,
                'passwd': current_password
            }
            
            if user_type:
                filter_kwargs['u_type'] = user_type
            
            # Find user
            users = user_login.objects.filter(**filter_kwargs)
            
            if not users.exists():
                return {
                    'success': False,
                    'error': 'Invalid current password'
                }
            
            # Update password
            user = users.first()
            user.passwd = new_password
            user.save()
            
            logger.info(f"Password changed for user: {username}")
            return {
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Password change failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }