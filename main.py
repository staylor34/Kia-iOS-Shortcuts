import datetime as dt
import os

from flask import Flask, request, jsonify

from hyundai_kia_connect_api import (
    VehicleManager,
    ClimateRequestOptions,
    Token,
)
from hyundai_kia_connect_api.ApiImpl import OTPRequest
from hyundai_kia_connect_api.const import OTP_NOTIFY_TYPE
from hyundai_kia_connect_api.exceptions import (
    AuthenticationError,
    AuthenticationOTPRequired,
)

app = Flask(__name__)

# =========================
# Environment Variables
# =========================
USERNAME = os.environ.get("KIA_USERNAME")
PASSWORD = os.environ.get("KIA_PASSWORD")
PIN = os.environ.get("KIA_PIN")
SECRET_KEY = os.environ.get("SECRET_KEY")
VEHICLE_ID = os.environ.get("VEHICLE_ID")  # Optional
KIA_REFRESH_TOKEN = os.environ.get("KIA_REFRESH_TOKEN")
KIA_DEVICE_ID = os.environ.get("KIA_DEVICE_ID")

missing = []
if not USERNAME:
    missing.append("KIA_USERNAME")
if not PASSWORD:
    missing.append("KIA_PASSWORD")
if not PIN:
    missing.append("KIA_PIN")
if not SECRET_KEY:
    missing.append("SECRET_KEY")

if missing:
    raise ValueError(f"Missing environment variables: {', '.join(missing)}")

# =========================
# Vehicle Manager
# =========================
saved_token = None

if KIA_REFRESH_TOKEN and KIA_DEVICE_ID:
    saved_token = Token(
        username=USERNAME,
        password=PASSWORD,
        access_token="",
        refresh_token=KIA_REFRESH_TOKEN,
        device_id=KIA_DEVICE_ID,
        valid_until=dt.datetime.min.replace(tzinfo=dt.timezone.utc),
        pin=str(PIN),
    )

vehicle_manager = VehicleManager(
    region=3,  # USA
    brand=1,   # Kia
    username=USERNAME,
    password=PASSWORD,
    pin=str(PIN),
    token=saved_token,
)

# =========================
# Helper Functions
# =========================
def authorize_request():
    return request.headers.get("Authorization") == SECRET_KEY

def ensure_authenticated():
    try:
        vehicle_manager.check_and_refresh_token()
    except AuthenticationError:
        raise
    except Exception:
        raise

def refresh_and_sync():
    """
    Refresh token and sync vehicle state
    """
    ensure_authenticated()
    vehicle_manager.update_all_vehicles_with_cached_state()


def get_vehicle_id():
    """
    Return VEHICLE_ID if provided, otherwise
    dynamically select the first vehicle.
    """
    if VEHICLE_ID:
        return VEHICLE_ID

    vehicles = vehicle_manager.vehicles
    if not vehicles:
        raise ValueError("No vehicles found on the Kia account.")

    first_vehicle_id = next(iter(vehicles.keys()))
    return first_vehicle_id


# =========================
# Logging
# =========================
@app.before_request
def log_request_info():
    print(f"Incoming request: {request.method} {request.path}")


# =========================
# Routes
# =========================
@app.route("/", methods=["GET"])
def root():
    return jsonify({
        "status": "OK",
        "service": "Kia Vehicle Control API"
    }), 200


@app.route("/auth_status", methods=["GET"])
def auth_status():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        ensure_authenticated()

        return jsonify({
            "status": "authenticated"
        }), 200

    except AuthenticationError as e:
        return jsonify({
            "status": "authentication_failed",
            "error_type": type(e).__name__,
            "message": str(e)
        }), 401

    except Exception as e:
        return jsonify({
            "status": "authentication_failed",
            "error_type": type(e).__name__,
            "message": str(e)
        }), 500


@app.route("/list_vehicles", methods=["GET"])
def list_vehicles():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()

        vehicles = vehicle_manager.vehicles
        if not vehicles:
            return jsonify({"error": "No vehicles found"}), 404

        vehicle_list = [
            {
                "name": v.name,
                "id": v.id,
                "model": v.model,
                "year": v.year
            }
            for v in vehicles.values()
        ]

        return jsonify({
            "status": "success",
            "vehicles": vehicle_list
        }), 200

    except AuthenticationError as e:
        return jsonify({
            "error": "Authentication failed",
            "details": str(e),
            "action": "Open Kia app and complete 2FA"
        }), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/start_climate", methods=["POST"])
def start_climate():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()
        vehicle_id = get_vehicle_id()

        climate_options = ClimateRequestOptions(
            set_temp=72,
            duration=10
        )

        result = vehicle_manager.start_climate(vehicle_id, climate_options)

        return jsonify({
            "status": "climate_started",
            "result": result
        }), 200

    except AuthenticationError as e:
        return jsonify({
            "error": "Authentication failed",
            "details": str(e),
            "action": "Open Kia app and complete 2FA"
        }), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/stop_climate", methods=["POST"])
def stop_climate():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()
        vehicle_id = get_vehicle_id()

        result = vehicle_manager.stop_climate(vehicle_id)

        return jsonify({
            "status": "climate_stopped",
            "result": result
        }), 200

    except AuthenticationError as e:
        return jsonify({
            "error": "Authentication failed",
            "details": str(e),
            "action": "Open Kia app and complete 2FA"
        }), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/unlock_car", methods=["POST"])
def unlock_car():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()
        vehicle_id = get_vehicle_id()

        result = vehicle_manager.unlock(vehicle_id)

        return jsonify({
            "status": "car_unlocked",
            "result": result
        }), 200

    except AuthenticationError as e:
        return jsonify({
            "error": "Authentication failed",
            "details": str(e),
            "action": "Open Kia app and complete 2FA"
        }), 401

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# @app.route("/lock_car", methods=["POST"])
# def lock_car():
#     if not authorize_request():
#         return jsonify({"error": "Unauthorized"}), 403

#     try:
#         refresh_and_sync()
#         vehicle_id = get_vehicle_id()
        
        # Issue the mechanical lock command
#         result = vehicle_manager.lock(vehicle_id)

#     except AuthenticationError as e:
#         return jsonify({
#             "error": "Authentication failed",
#             "details": str(e),
#           "action": "Open Kia app and complete 2FA"
#         }), 401
#     except Exception as e:
        # Catch any unpatched API library hiccups and verify it locked
#         pass

    # Force a clean JSON success string to your iPhone
#     return jsonify({
#         "status": "success"
#     }), 200

@app.route("/lock_car", methods=["POST"])
def lock_car():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    stage = "starting"

    try:
        stage = "refreshing_vehicle_state"
        refresh_and_sync()

        stage = "getting_vehicle_id"
        vehicle_id = get_vehicle_id()

        stage = "sending_lock_command"
        result = vehicle_manager.lock(vehicle_id)

        return jsonify({
            "status": "lock_command_completed",
            "result": result
        }), 200

    except AuthenticationError as e:
        return jsonify({
            "status": "authentication_failed",
            "stage": stage,
            "error_type": type(e).__name__,
            "message": str(e)
        }), 401

    except Exception as e:
        return jsonify({
            "status": "lock_result_unknown",
            "stage": stage,
            "error_type": type(e).__name__,
            "message": str(e),
            "note": (
                "The Kia server may have accepted the lock command "
                "even though the library reported an error."
            )
        }), 202

@app.route("/vehicle_status", methods=["GET"])
def vehicle_status():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        refresh_and_sync()
        vehicle_id = get_vehicle_id()
        vehicle = vehicle_manager.get_vehicle(vehicle_id)

        return jsonify({
            "status": "success",
            "vehicle": {
                "name": getattr(vehicle, "name", None),
                "model": getattr(vehicle, "model", None),
                "year": getattr(vehicle, "year", None),

                # Likely useful state fields
                "is_locked": getattr(vehicle, "is_locked", None),
                "engine_is_running": getattr(
                    vehicle, "engine_is_running", None
                ),
                "doors": getattr(vehicle, "doors", None),
                "trunk_is_open": getattr(
                    vehicle, "trunk_is_open", None
                ),
                "hood_is_open": getattr(
                    vehicle, "hood_is_open", None
                ),
                "last_updated_at": str(
                    getattr(vehicle, "last_updated_at", None)
                )
            }
        }), 200

    except AuthenticationError as e:
        return jsonify({
            "error": "Authentication failed",
            "details": str(e),
            "action": "Open Kia app and complete 2FA"
        }), 401

    except Exception as e:
        return jsonify({
            "error": "Unable to retrieve vehicle status",
            "details": str(e)
        }), 500

@app.route("/otp/send", methods=["POST"])
def otp_send():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = request.get_json(silent=True) or {}
        requested_method = str(data.get("method", "email")).lower()

        # Start a fresh login. If OTP is required, VehicleManager stores
        # the OTPRequest in vehicle_manager.otp_request.
        login_result = vehicle_manager.login()

        if login_result is True:
            return jsonify({
                "status": "already_authenticated"
            }), 200

        if not isinstance(login_result, OTPRequest):
            return jsonify({
                "status": "unexpected_login_result",
                "result_type": type(login_result).__name__
            }), 500

        if requested_method == "email":
            if not login_result.has_email:
                return jsonify({
                    "status": "email_unavailable",
                    "message": "Kia did not offer email as an OTP destination."
                }), 400

            notify_type = OTP_NOTIFY_TYPE.EMAIL

        elif requested_method in ("sms", "phone"):
            if not login_result.has_sms:
                return jsonify({
                    "status": "sms_unavailable",
                    "message": "Kia did not offer SMS as an OTP destination."
                }), 400

            notify_type = OTP_NOTIFY_TYPE.SMS

        else:
            return jsonify({
                "status": "invalid_method",
                "message": "Use 'email' or 'sms'."
            }), 400

        vehicle_manager.send_otp(notify_type)

        # Return enough information to reconstruct the OTP challenge
        # if Vercel sends the verification request to another instance.
        return jsonify({
            "status": "otp_sent",
            "method": requested_method,
            "challenge": {
                "otp_key": login_result.otp_key,
                "request_id": login_result.request_id,
                "email": login_result.email,
                "sms": login_result.sms,
                "has_email": login_result.has_email,
                "has_sms": login_result.has_sms,
                "device_id": vehicle_manager.api.device_id
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "otp_send_failed",
            "error_type": type(e).__name__,
            "message": str(e)
        }), 500


@app.route("/otp/verify", methods=["POST"])
def otp_verify():
    if not authorize_request():
        return jsonify({"error": "Unauthorized"}), 403

    try:
        data = request.get_json(silent=True) or {}

        otp_code = str(data.get("otp_code", "")).strip()
        otp_key = str(data.get("otp_key", "")).strip()
        request_id = str(data.get("request_id", "")).strip()
        device_id = str(data.get("device_id", "")).strip()

        missing_fields = []

        if not otp_code:
            missing_fields.append("otp_code")
        if not otp_key:
            missing_fields.append("otp_key")
        if not request_id:
            missing_fields.append("request_id")
        if not device_id:
            missing_fields.append("device_id")

        if missing_fields:
            return jsonify({
                "status": "missing_fields",
                "missing": missing_fields
            }), 400

        # Restore the same virtual Kia device used to request the OTP.
        vehicle_manager.api.device_id = device_id

        # Reconstruct the challenge in case this is a different
        # Vercel serverless instance.
        vehicle_manager.otp_request = OTPRequest(
            otp_key=otp_key,
            request_id=request_id,
            email=None,
            sms=None,
            has_email=True,
            has_sms=True,
        )

        vehicle_manager.verify_otp_and_complete_login(otp_code)

        token = vehicle_manager.token

        return jsonify({
            "status": "otp_verified",
            "message": (
                "Save refresh_token and device_id as private Vercel "
                "environment variables, then redeploy."
            ),
            "vercel_environment_variables": {
                "KIA_REFRESH_TOKEN": token.refresh_token,
                "KIA_DEVICE_ID": token.device_id
            }
        }), 200

    except Exception as e:
        return jsonify({
            "status": "otp_verification_failed",
            "error_type": type(e).__name__,
            "message": str(e)
        }), 500
# =========================
# App Entry
# =========================
if __name__ == "__main__":
    print("Starting Kia Vehicle Control API...")
    app.run(host="0.0.0.0", port=8080)
