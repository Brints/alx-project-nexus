import geoip2.database
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Extract client IP from headers"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def get_country_from_ip(ip_address):
    """
    Resolves IP address to ISO Country Code (e.g., 'NG', 'US', 'GB') using GeoIP2.
    """
    # Handle Localhost / Private IPs immediately
    if ip_address in ['127.0.0.1', 'localhost', '::1'] or ip_address.startswith('192.168.'):
        return None

    db_path = settings.GEOIP_PATH / settings.GEOIP_COUNTRY

    try:
        # standard 'with' statement ensures the file reader closes automatically
        with geoip2.database.Reader(db_path) as reader:
            response = reader.country(ip_address)
            return response.country.iso_code

    except FileNotFoundError:
        logger.error(f"GeoIP database not found at {db_path}")
        return None
    except geoip2.errors.AddressNotFoundError:
        # The IP is valid but not in the database (common for some private IPs)
        return None
    except Exception as e:
        logger.error(f"GeoIP lookup failed: {str(e)}")
        return None