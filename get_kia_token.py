import getpass

from hyundai_kia_connect_api import VehicleManager
from hyundai_kia_connect_api.ApiImpl import OTPRequest
from hyundai_kia_connect_api.const import OTP_NOTIFY_TYPE


def main():
    username = input("Kia email: ").strip()
    password = getpass.getpass("Kia password: ")
    pin = getpass.getpass("Kia PIN: ")

    manager = VehicleManager(
        region=3,
        brand=1,
        username=username,
        password=password,
        pin=pin,
    )

    print("\nStarting Kia login...")

    login_result = manager.login()

    if login_result is True:
        print("Login succeeded without OTP.")
    elif isinstance(login_result, OTPRequest):
        print(
            f"Sending OTP to: "
            f"{login_result.email or 'the email registered with Kia'}"
        )

        manager.send_otp(OTP_NOTIFY_TYPE.EMAIL)

        otp_code = input(
            "Enter the code from the newest Kia email: "
        ).strip()

        manager.verify_otp_and_complete_login(otp_code)
    else:
        raise RuntimeError(
            f"Unexpected login result: {type(login_result).__name__}"
        )

    token = manager.token

    if not token or not token.refresh_token or not token.device_id:
        raise RuntimeError(
            "Login succeeded, but no refresh token or device ID was returned."
        )

    print("\nSUCCESS")
    print("\nAdd these private environment variables to Vercel:")
    print(f"\nKIA_REFRESH_TOKEN={token.refresh_token}")
    print(f"\nKIA_DEVICE_ID={token.device_id}")
    print(
        "\nKeep these values private. "
        "Do not paste the refresh token into chat or GitHub."
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\nERROR: {type(exc).__name__}: {exc}")
