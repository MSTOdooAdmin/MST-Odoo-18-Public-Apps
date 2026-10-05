# -*- coding: utf-8 -*-

"""Small, defensive helpers used by login-history geolocation.

The module intentionally treats geolocation as best-effort.  A GeoIP database,
browser permission, reverse-geocoding service, or proxy configuration may be
missing; none of those conditions should ever prevent an Odoo login.
"""

import ipaddress
import json
import logging
from collections.abc import Mapping
from urllib.parse import urlencode
from urllib.request import Request, urlopen

_logger = logging.getLogger(__name__)

_REVERSE_GEOCODE_DEFAULT_URL = "https://nominatim.openstreetmap.org/reverse"
_REVERSE_GEOCODE_TIMEOUT = 3.0


def valid_coordinates(latitude, longitude):
    """Return normalized coordinate strings or (False, False)."""
    try:
        latitude = float(latitude)
        longitude = float(longitude)
    except (TypeError, ValueError):
        return False, False

    if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
        return False, False

    # Six decimals are more than sufficient for a login audit while avoiding
    # unnecessarily precise storage/display noise.
    return f"{latitude:.6f}", f"{longitude:.6f}"


def _mapping_get(value, *keys):
    if isinstance(value, Mapping):
        for key in keys:
            result = value.get(key)
            if result not in (None, False, ""):
                return result
    return None


def _attr_get(value, *attrs):
    for attr in attrs:
        try:
            result = getattr(value, attr, None)
        except Exception:
            result = None
        if result not in (None, False, ""):
            return result
    return None


def _name_from(value):
    if value in (None, False, ""):
        return ""
    if isinstance(value, str):
        return value
    result = _mapping_get(value, "name", "country_name", "city_name")
    if result:
        return str(result)
    result = _attr_get(value, "name")
    return str(result or "")


def geoip_values(geoip):
    """Normalize Odoo 20/GeoIP2 response variants into our audit fields.

    Odoo deployments can expose the location through a GeoIP2 response object
    (``request.geoip.country.name``) or a mapping-like compatibility object.
    Supporting both prevents city/country from disappearing across deployment
    styles and minor framework changes.
    """
    values = {
        "country": "",
        "region": "",
        "city": "",
        "geo_latitude": "",
        "geo_longitude": "",
        "full_location": "",
    }
    if not geoip:
        return values

    try:
        country = (
            _name_from(_attr_get(geoip, "country"))
            or str(_attr_get(geoip, "country_name") or "")
            or _name_from(_mapping_get(geoip, "country_name", "country"))
        )

        city = (
            _name_from(_attr_get(geoip, "city"))
            or str(_attr_get(geoip, "city_name") or "")
            or _name_from(_mapping_get(geoip, "city_name", "city"))
        )

        region = ""
        subdivisions = _attr_get(geoip, "subdivisions")
        if subdivisions:
            try:
                first = subdivisions[0]
            except (TypeError, IndexError, KeyError):
                first = None
            if first:
                region = _name_from(first) or str(
                    _attr_get(first, "iso_code") or _mapping_get(first, "iso_code") or ""
                )
        region = region or str(
            _attr_get(geoip, "region")
            or _mapping_get(geoip, "region", "region_name", "subdivision")
            or ""
        )

        latitude = ""
        longitude = ""
        location = _attr_get(geoip, "location")
        if location:
            latitude = _attr_get(location, "latitude") or _mapping_get(location, "latitude")
            longitude = _attr_get(location, "longitude") or _mapping_get(location, "longitude")
        if latitude in (None, False, ""):
            latitude = _attr_get(geoip, "latitude") or _mapping_get(geoip, "latitude")
        if longitude in (None, False, ""):
            longitude = _attr_get(geoip, "longitude") or _mapping_get(geoip, "longitude")

        latitude, longitude = valid_coordinates(latitude, longitude)
        values.update({
            "country": country.strip(),
            "region": region.strip(),
            "city": city.strip(),
            "geo_latitude": latitude or "",
            "geo_longitude": longitude or "",
        })
        values["full_location"] = ", ".join(
            item for item in [values["city"], values["region"], values["country"]] if item
        )
    except Exception:
        _logger.debug("Unable to normalize Odoo GeoIP response", exc_info=True)

    return values


def client_ip(http_request):
    """Return the client address provided by Werkzeug/Odoo.

    With Odoo ``proxy_mode = True`` Werkzeug already resolves the trusted
    X-Forwarded-For chain.  We deliberately do not trust forwarding headers
    ourselves when proxy mode is disabled.
    """
    try:
        value = (http_request.remote_addr or "").strip()
        if not value:
            return ""
        # Normalize IPv4-mapped IPv6 values when possible; preserve any value
        # Werkzeug provides if normalization is not applicable.
        try:
            parsed = ipaddress.ip_address(value)
            if getattr(parsed, "ipv4_mapped", None):
                return str(parsed.ipv4_mapped)
            return str(parsed)
        except ValueError:
            return value
    except Exception:
        return ""


def _address_value(address, *keys):
    for key in keys:
        value = address.get(key)
        if value:
            return str(value).strip()
    return ""


def reverse_geocode(env, latitude, longitude):
    """Best-effort reverse geocoding for browser coordinates.

    Odoo GeoIP maps an IP to a location, so localhost/LAN users with browser
    coordinates still need a reverse geocoder for City/Country.  This fallback
    uses the public Nominatim endpoint by default and can be disabled or pointed
    at an internal compatible endpoint with system parameters:

      * mst_advanced_login_history.reverse_geocoding_enabled (default: True)
      * mst_advanced_login_history.reverse_geocoding_url

    Any network/provider failure returns empty strings and never blocks login.
    """
    latitude, longitude = valid_coordinates(latitude, longitude)
    empty = {
        "country": "",
        "region": "",
        "city": "",
        "full_location": "",
    }
    if latitude is False or longitude is False:
        return empty

    try:
        params = env["ir.config_parameter"].sudo()
        enabled = str(
            params.get_param(
                "mst_advanced_login_history.reverse_geocoding_enabled",
                "True",
            )
        ).strip().lower() not in {"0", "false", "no", "off"}
        if not enabled:
            return empty

        endpoint = (
            params.get_param(
                "mst_advanced_login_history.reverse_geocoding_url",
                _REVERSE_GEOCODE_DEFAULT_URL,
            )
            or _REVERSE_GEOCODE_DEFAULT_URL
        ).strip()
        # Do not allow arbitrary non-http schemes from a configurable value.
        if not endpoint.startswith(("https://", "http://")):
            return empty

        query = urlencode({
            "format": "jsonv2",
            "lat": latitude,
            "lon": longitude,
            "zoom": 18,
            "addressdetails": 1,
            "accept-language": "en",
        })
        req = Request(
            f"{endpoint}?{query}",
            headers={
                "User-Agent": (
                    "MindSpark-Odoo-Login-History/20.0 "
                    "(+https://mindsparktechnologies.com)"
                ),
                "Accept": "application/json",
            },
        )
        with urlopen(req, timeout=_REVERSE_GEOCODE_TIMEOUT) as response:  # nosec B310 - endpoint scheme validated above
            raw = response.read(256 * 1024)
        payload = json.loads(raw.decode("utf-8")) if raw else {}
        address = payload.get("address") or {}

        city = _address_value(
            address,
            "city",
            "town",
            "village",
            "municipality",
            "city_district",
            "suburb",
            "county",
        )
        region = _address_value(address, "state", "region", "state_district", "county")
        country = _address_value(address, "country")
        full_location = ", ".join(item for item in [city, region, country] if item)
        if not full_location:
            full_location = str(payload.get("display_name") or "").strip()

        return {
            "country": country,
            "region": region,
            "city": city,
            "full_location": full_location,
        }
    except Exception:
        _logger.debug(
            "Browser-coordinate reverse geocoding was unavailable; login tracking continues without city/country.",
            exc_info=True,
        )
        return empty


def store_browser_location_in_session(
    session,
    env,
    latitude,
    longitude,
    city="",
    region="",
    country="",
    full_location="",
):
    latitude, longitude = valid_coordinates(latitude, longitude)
    if latitude is False or longitude is False:
        return False

    old_lat = session.get("advanced_login_latitude")
    old_lon = session.get("advanced_login_longitude")
    same_coordinates = old_lat == latitude and old_lon == longitude

    session["advanced_login_latitude"] = latitude
    session["advanced_login_longitude"] = longitude

    city = str(city or "").strip()
    region = str(region or "").strip()
    country = str(country or "").strip()
    full_location = str(full_location or "").strip()

    if not full_location:
        full_location = ", ".join(value for value in [city, region, country] if value)

    if city or region or country or full_location:
        session["advanced_login_city"] = city
        session["advanced_login_region"] = region
        session["advanced_login_country"] = country
        session["advanced_login_full_location"] = full_location
        return True

    # Reuse a previous result for the same coordinates to avoid duplicate
    # reverse-geocoding calls during the login-page -> backend transition.
    if same_coordinates and any(
        session.get(key)
        for key in (
            "advanced_login_city",
            "advanced_login_region",
            "advanced_login_country",
        )
    ):
        return True

    resolved = reverse_geocode(env, latitude, longitude)
    session["advanced_login_city"] = resolved.get("city", "")
    session["advanced_login_region"] = resolved.get("region", "")
    session["advanced_login_country"] = resolved.get("country", "")
    session["advanced_login_full_location"] = resolved.get("full_location", "")
    return True


def browser_location_from_session(session):
    if not session:
        return {
            "latitude": "",
            "longitude": "",
            "browser_city": "",
            "browser_region": "",
            "browser_country": "",
            "browser_full_location": "",
        }
    return {
        "latitude": session.get("advanced_login_latitude", ""),
        "longitude": session.get("advanced_login_longitude", ""),
        "browser_city": session.get("advanced_login_city", ""),
        "browser_region": session.get("advanced_login_region", ""),
        "browser_country": session.get("advanced_login_country", ""),
        "browser_full_location": session.get("advanced_login_full_location", ""),
    }
