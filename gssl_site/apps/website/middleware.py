"""Response headers Django 5.2 does not set on its own."""

from django.conf import settings


class SecurityHeadersMiddleware:
    """
    Adds Content-Security-Policy and Permissions-Policy to every response
    Django renders. Static files are answered by WhiteNoise before this runs.

    The admin gets a policy that also allows inline style attributes, which a
    few admin widgets use. The console gets the site's own policy plus blob:
    images, so an upload can be previewed before it is saved. In development
    the policy is report-only, so Django's own debug pages (inline CSS and JS)
    still render while violations show in the browser console.
    """

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin_prefix = "/" + settings.ADMIN_URL
        self.console_prefix = "/" + settings.CONSOLE_URL

    def policy_for(self, path: str) -> str:
        if path.startswith(self.console_prefix):
            return settings.CONTENT_SECURITY_POLICY_CONSOLE
        if path.startswith(self.admin_prefix):
            return settings.CONTENT_SECURITY_POLICY_ADMIN
        return settings.CONTENT_SECURITY_POLICY

    def __call__(self, request):
        response = self.get_response(request)
        policy = self.policy_for(request.path)
        header = (
            "Content-Security-Policy-Report-Only"
            if settings.CONTENT_SECURITY_POLICY_REPORT_ONLY
            else "Content-Security-Policy"
        )
        response.headers.setdefault(header, policy)
        response.headers.setdefault("Permissions-Policy", settings.PERMISSIONS_POLICY)
        return response
